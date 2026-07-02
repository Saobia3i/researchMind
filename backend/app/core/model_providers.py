import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)

ProviderName = Literal["groq", "openai", "gemini", "perplexity"]


@dataclass
class ModelUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ModelResponse:
    provider: ProviderName
    model: str
    content: str
    usage: ModelUsage
    estimated_cost_usd: float
    skipped: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class ModelPricing:
    input_per_1m: float
    output_per_1m: float
    billing_note: str


MODEL_PRICING: dict[ProviderName, ModelPricing] = {
    "groq": ModelPricing(
        input_per_1m=0.59,
        output_per_1m=0.79,
        billing_note="Estimated market-rate value; free-tier keys may be quota-limited.",
    ),
    "openai": ModelPricing(
        input_per_1m=0.15,
        output_per_1m=0.60,
        billing_note="Paid/credit-based API usage. Not used by the default free-friendly workflow.",
    ),
    "gemini": ModelPricing(
        input_per_1m=0.0,
        output_per_1m=0.0,
        billing_note="Configured as free-tier/quota usage for this project.",
    ),
    "perplexity": ModelPricing(
        input_per_1m=1.00,
        output_per_1m=1.00,
        billing_note="Paid API usage. Adapter is optional and disabled by the default workflow.",
    ),
}

MODEL_NAMES: dict[ProviderName, str] = {
    "groq": settings.groq_model,
    "openai": settings.openai_model,
    "gemini": settings.gemini_model,
    "perplexity": settings.perplexity_model,
}


def provider_available(provider: ProviderName) -> bool:
    return bool(
        {
            "groq": settings.groq_api_key,
            "openai": settings.openai_api_key,
            "gemini": settings.gemini_api_key,
            "perplexity": settings.perplexity_api_key,
        }[provider]
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def estimate_message_tokens(messages: list[dict]) -> int:
    return sum(estimate_tokens(str(m.get("content", ""))) for m in messages)


def estimate_cost(provider: ProviderName, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING[provider]
    return (
        (prompt_tokens / 1_000_000) * pricing.input_per_1m
        + (completion_tokens / 1_000_000) * pricing.output_per_1m
    )


class CostBudget:
    def __init__(self, limit_usd: float):
        self.limit_usd = max(0.0, limit_usd)
        self.spent_usd = 0.0
        self.events: list[dict] = []

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    def can_spend(self, estimated_cost_usd: float) -> bool:
        if estimated_cost_usd <= 0:
            return True
        return self.spent_usd + estimated_cost_usd <= self.limit_usd

    def record(self, response: ModelResponse, stage: str) -> None:
        self.spent_usd += response.estimated_cost_usd
        self.events.append(
            {
                "stage": stage,
                "provider": response.provider,
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "estimated_cost_usd": round(response.estimated_cost_usd, 6),
                "billing_note": MODEL_PRICING[response.provider].billing_note,
                "skipped": response.skipped,
                "reason": response.reason,
            }
        )

    def to_dict(self) -> dict:
        return {
            "limit_usd": round(self.limit_usd, 6),
            "spent_usd": round(self.spent_usd, 6),
            "remaining_usd": round(self.remaining_usd, 6),
            "events": self.events,
        }


def skipped_response(provider: ProviderName, reason: str) -> ModelResponse:
    return ModelResponse(
        provider=provider,
        model=MODEL_NAMES[provider],
        content="",
        usage=ModelUsage(),
        estimated_cost_usd=0.0,
        skipped=True,
        reason=reason,
    )


def call_model(
    provider: ProviderName,
    messages: list[dict],
    *,
    max_tokens: int = 900,
    temperature: float = 0.2,
    budget: CostBudget | None = None,
    stage: str = "llm_call",
) -> ModelResponse:
    if not provider_available(provider):
        response = skipped_response(provider, f"{provider.upper()} API key is not configured.")
        if budget:
            budget.record(response, stage)
        return response

    estimated_prompt_tokens = estimate_message_tokens(messages)
    estimated_call_cost = estimate_cost(provider, estimated_prompt_tokens, max_tokens)
    if budget and not budget.can_spend(estimated_call_cost):
        response = skipped_response(
            provider,
            f"Skipped to stay within budget. Estimated call cost ${estimated_call_cost:.6f}, remaining ${budget.remaining_usd:.6f}.",
        )
        budget.record(response, stage)
        return response

    model = MODEL_NAMES[provider]
    try:
        if provider == "groq":
            response = _call_groq(model, messages, max_tokens, temperature)
        elif provider == "openai":
            response = _call_openai(model, messages, max_tokens, temperature)
        elif provider == "perplexity":
            response = _call_perplexity(model, messages, max_tokens, temperature)
        else:
            response = _call_gemini(model, messages, max_tokens, temperature)
    except Exception as exc:
        logger.exception("%s call failed", provider)
        response = skipped_response(provider, f"{provider} call failed: {exc}")

    if budget:
        budget.record(response, stage)
    return response


def _call_groq(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> ModelResponse:
    client = Groq(api_key=settings.groq_api_key)
    raw = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = raw.choices[0].message.content or ""
    usage = ModelUsage(
        prompt_tokens=getattr(raw.usage, "prompt_tokens", estimate_message_tokens(messages)),
        completion_tokens=getattr(raw.usage, "completion_tokens", estimate_tokens(content)),
    )
    return ModelResponse("groq", model, content, usage, estimate_cost("groq", usage.prompt_tokens, usage.completion_tokens))


def _call_openai(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> ModelResponse:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    with httpx.Client(timeout=60) as client:
        raw = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        raw.raise_for_status()
        data = raw.json()

    content = data["choices"][0]["message"]["content"] or ""
    raw_usage = data.get("usage", {})
    usage = ModelUsage(
        prompt_tokens=raw_usage.get("prompt_tokens", estimate_message_tokens(messages)),
        completion_tokens=raw_usage.get("completion_tokens", estimate_tokens(content)),
    )
    return ModelResponse("openai", model, content, usage, estimate_cost("openai", usage.prompt_tokens, usage.completion_tokens))


def _call_perplexity(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> ModelResponse:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {settings.perplexity_api_key}"}
    with httpx.Client(timeout=90) as client:
        raw = client.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers)
        raw.raise_for_status()
        data = raw.json()

    content = data["choices"][0]["message"]["content"] or ""
    raw_usage = data.get("usage", {})
    usage = ModelUsage(
        prompt_tokens=raw_usage.get("prompt_tokens", estimate_message_tokens(messages)),
        completion_tokens=raw_usage.get("completion_tokens", estimate_tokens(content)),
    )
    return ModelResponse(
        "perplexity",
        model,
        content,
        usage,
        estimate_cost("perplexity", usage.prompt_tokens, usage.completion_tokens),
    )


def _call_gemini(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> ModelResponse:
    system_parts = []
    contents = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if role == "system":
            system_parts.append(content)
        else:
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": content}],
                }
            )

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    with httpx.Client(timeout=60) as client:
        raw = client.post(url, params={"key": settings.gemini_api_key}, json=payload)
        raw.raise_for_status()
        data = raw.json()

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    content = "\n".join(part.get("text", "") for part in parts).strip()
    raw_usage = data.get("usageMetadata", {})
    usage = ModelUsage(
        prompt_tokens=raw_usage.get("promptTokenCount", estimate_message_tokens(messages)),
        completion_tokens=raw_usage.get("candidatesTokenCount", estimate_tokens(content)),
    )
    return ModelResponse(
        "gemini",
        model,
        content,
        usage,
        estimate_cost("gemini", usage.prompt_tokens, usage.completion_tokens),
    )
