import json
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None


def call_llm_structured(
    messages: list[dict],
    system: str,
    output_schema: dict,
) -> dict:
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    schema_instruction = f"""
You MUST respond with ONLY valid JSON that matches this schema exactly:
{json.dumps(output_schema, indent=2)}

No explanation, no markdown, no extra text. Just the JSON object.
"""
    all_messages = [
        {"role": "system", "content": system + "\n\n" + schema_instruction}
    ] + messages

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2048,
        messages=all_messages,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)
