"""Claude LLM Client.
Anthropic API wrapper with exponential backoff retry, timeout protection,
JSON-schema validation, single-attempt repair retry, persistent response cache,
and budget guard integration.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel
from ...store import now
from .budget_guard import BudgetGuard

T = TypeVar("T", bound=BaseModel)


class LLMClientError(RuntimeError):
    """Raised when an unrecoverable LLM call failure occurs."""
    pass


class ClaudeClient:
    """Robust Anthropic Claude client with caching, retry, and schema validation."""

    def __init__(
        self,
        api_key: str,
        budget_guard: BudgetGuard,
        db: Optional[sqlite3.Connection] = None,
        owner_id: str = "local-owner",
        cache_dir: Optional[Path] = None,
        max_retries: int = 3,
        timeout_s: int = 60,
    ):
        self.api_key = api_key
        self.budget_guard = budget_guard
        self.db = db
        self.owner_id = owner_id
        self.cache_dir = cache_dir or Path("./data/llm_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.timeout_s = timeout_s

        self._anthropic_client = None
        if self.api_key:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=self.api_key, timeout=float(self.timeout_s))
            except Exception:
                self._anthropic_client = None

    def _cache_key(self, model: str, system_prompt: str, user_prompt: str, schema_name: str) -> str:
        h = hashlib.sha256()
        h.update(model.encode("utf-8"))
        h.update(system_prompt.encode("utf-8"))
        h.update(user_prompt.encode("utf-8"))
        h.update(schema_name.encode("utf-8"))
        return h.hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[dict]:
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _save_cached_response(self, cache_key: str, data: dict) -> None:
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def call_structured(
        self,
        agent: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.0,
    ) -> T:
        """Execute a structured completion returning a validated Pydantic model."""
        schema_name = response_model.__name__
        cache_key = self._cache_key(model, system_prompt, user_prompt, schema_name)

        # 1. Check cache
        cached = self._get_cached_response(cache_key)
        if cached:
            # Audit cached call
            self._record_db_call(agent, cache_key, 0, 0, cached=True, latency_ms=0)
            return response_model.model_validate(cached)

        # 2. Check budget before invoking
        self.budget_guard.check_can_call(agent)

        if not self._anthropic_client:
            raise LLMClientError("Anthropic client is not initialized (missing ANTHROPIC_API_KEY)")

        # 3. Call API with retry loop
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        full_system = f"{system_prompt}\n\nYou MUST respond with valid JSON matching this schema:\n{schema_json}"
        
        raw_text = ""
        tokens_in = 0
        tokens_out = 0
        start_time = time.time()
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._anthropic_client.messages.create(
                    model=model,
                    system=full_system,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=temperature,
                    max_tokens=4096,
                )
                raw_text = response.content[0].text
                tokens_in = getattr(response.usage, "input_tokens", 0)
                tokens_out = getattr(response.usage, "output_tokens", 0)
                break
            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries:
                    latency_ms = int((time.time() - start_time) * 1000)
                    self._record_db_call(agent, cache_key, 0, 0, cached=False, latency_ms=latency_ms, error=str(exc))
                    raise LLMClientError(f"LLM call failed after {self.max_retries} attempts: {exc}") from exc
                time.sleep(2 ** attempt)

        latency_ms = int((time.time() - start_time) * 1000)
        self.budget_guard.record_usage(agent, tokens_in, tokens_out)

        # 4. Parse and validate JSON (with one repair retry if malformed)
        parsed_dict = None
        try:
            parsed_dict = self._extract_json(raw_text)
            validated = response_model.model_validate(parsed_dict)
            self._save_cached_response(cache_key, parsed_dict)
            self._record_db_call(agent, cache_key, tokens_in, tokens_out, cached=False, latency_ms=latency_ms)
            return validated
        except Exception as parse_err:
            # One repair retry
            repaired = self._attempt_repair(agent, model, full_system, raw_text, str(parse_err), response_model)
            if repaired:
                self._save_cached_response(cache_key, repaired.model_dump())
                self._record_db_call(agent, cache_key, tokens_in, tokens_out, cached=False, latency_ms=latency_ms)
                return repaired
            raise LLMClientError(f"Failed to validate response against {schema_name}: {parse_err}. Raw: {raw_text[:200]}") from parse_err

    def _extract_json(self, text: str) -> dict:
        """Extract JSON block from model response."""
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        return json.loads(clean)

    def _attempt_repair(
        self,
        agent: str,
        model: str,
        system_prompt: str,
        bad_output: str,
        error_msg: str,
        response_model: Type[T],
    ) -> Optional[T]:
        """Perform one repair retry on JSON validation failure."""
        repair_prompt = (
            f"Your previous output failed validation with error:\n{error_msg}\n\n"
            f"Here was your previous output:\n{bad_output}\n\n"
            f"Please output ONLY corrected, strictly valid JSON."
        )
        try:
            self.budget_guard.check_can_call(agent)
            response = self._anthropic_client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.0,
                max_tokens=4096,
            )
            raw = response.content[0].text
            tokens_in = getattr(response.usage, "input_tokens", 0)
            tokens_out = getattr(response.usage, "output_tokens", 0)
            self.budget_guard.record_usage(agent, tokens_in, tokens_out)
            parsed = self._extract_json(raw)
            return response_model.model_validate(parsed)
        except Exception:
            return None

    def _record_db_call(
        self,
        agent: str,
        prompt_hash: str,
        tokens_in: int,
        tokens_out: int,
        cached: bool = False,
        latency_ms: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Record telemetry to SQLite odin_llm_calls table if connection available."""
        if not self.db:
            return
        try:
            import uuid
            call_id = str(uuid.uuid4())
            self.db.execute(
                """
                INSERT INTO odin_llm_calls(call_id, owner_id, agent, prompt_hash, tokens_in, tokens_out, cached, latency_ms, error, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    self.owner_id,
                    agent,
                    prompt_hash,
                    tokens_in,
                    tokens_out,
                    1 if cached else 0,
                    latency_ms,
                    error,
                    now(),
                ),
            )
        except Exception:
            pass
