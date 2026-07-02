from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None


def call_llm(
    messages: list[dict],
    system: str = "You are a helpful research assistant.",
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 1024,
) -> str:
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    all_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=all_messages,
    )
    return response.choices[0].message.content
