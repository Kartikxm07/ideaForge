"""Ollama is the only inference endpoint, constrained to loopback."""
import json
import httpx
from pydantic import ValidationError
from .config import Settings
from .tools import Step, validate_steps


class ModelUnavailable(Exception):
    pass


class OllamaProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def health(self) -> dict:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                response = client.get(f"{self.settings.ollama_url}/api/tags")
                response.raise_for_status()
                models = [item.get("name", "") for item in response.json().get("models", [])]
        except (httpx.HTTPError, ValueError) as exc:
            return {"available": False, "model": self.settings.ollama_model, "reason": type(exc).__name__}
        available = any(name == self.settings.ollama_model or name.split(":")[0] == self.settings.ollama_model for name in models)
        return {"available": available, "model": self.settings.ollama_model, "reason": None if available else "model_missing"}

    def plan(self, prompt: str) -> list[Step]:
        instructions = (
            "Return only a JSON array of 1 to 8 steps. Each step has tool_id, text, and use_previous. "
            "Allowed tool_id values: text.uppercase, text.word_count, memory.save. "
            "Only use memory.save when the user explicitly asks to remember text. "
            "No shell, files, URLs, or other tools. User request: " + prompt
        )
        try:
            with httpx.Client(timeout=30, trust_env=False) as client:
                response = client.post(
                    f"{self.settings.ollama_url}/api/generate",
                    json={"model": self.settings.ollama_model, "prompt": instructions, "format": "json", "stream": False, "options": {"num_predict": 512}},
                )
                response.raise_for_status()
                data = json.loads(response.json()["response"])
            steps = [Step.model_validate(item) for item in data]
            validate_steps(steps)
            return steps
        except (httpx.HTTPError, ValueError, KeyError, TypeError, ValidationError) as exc:
            raise ModelUnavailable(f"Local model unavailable or returned an invalid plan: {type(exc).__name__}") from exc
