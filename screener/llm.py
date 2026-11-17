"""Thin wrapper around the Groq client: retries on rate limits, tolerant JSON parsing."""
import json
import re
import time

from groq import Groq, RateLimitError

DEFAULT_MODEL = "openai/gpt-oss-120b"
MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def parse_json_object(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("The model did not return valid JSON.")
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("The model returned JSON, but not an object.")
    return data


class LLM:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, max_retries: int = 5):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.max_retries = max_retries

    def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        kwargs = {"model": self.model, "messages": messages, "temperature": 0}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return (response.choices[0].message.content or "").strip()
            except RateLimitError:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(min(2 ** (attempt + 1), 30))
        return ""

    def json(self, messages: list[dict]) -> dict:
        return parse_json_object(self.chat(messages, json_mode=True))
