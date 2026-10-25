"""ODIN System Configuration.
Loads settings from environment variables with sensible defaults.
Never prints or hardcodes secret keys.
"""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class OdinConfig:
    # LLM Settings (Anthropic Claude only)
    anthropic_api_key: str = ""
    model_heavy: str = "claude-3-7-sonnet-20250219"
    model_light: str = "claude-3-5-haiku-20241022"
    temperature: float = 0.0

    # Multi-Agent Bounded Loop Controls
    max_clarify_per_finding: int = 2
    max_debate_rounds: int = 2
    max_iterations_per_checkpoint: int = 3

    # Safety & Resource Budget Guards
    max_llm_calls_total: int = 100
    max_tokens_total: int = 500_000
    per_agent_call_cap: int = 30
    llm_retries: int = 3
    llm_timeout_s: int = 60

    # Cache directory for responses
    cache_dir: Path = Path("./data/llm_cache")

    @classmethod
    def from_env(cls) -> "OdinConfig":
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        model_h = os.getenv("MODEL_HEAVY", "claude-3-7-sonnet-20250219").strip()
        model_l = os.getenv("MODEL_LIGHT", "claude-3-5-haiku-20241022").strip()
        
        # Fallback to 3.5 Sonnet if 3.7 is explicitly not configured or rejected
        if not model_h:
            model_h = "claude-3-5-sonnet-20241022"
        if not model_l:
            model_l = "claude-3-5-haiku-20241022"

        return cls(
            anthropic_api_key=key,
            model_heavy=model_h,
            model_light=model_l,
            temperature=float(os.getenv("TEMPERATURE", "0.0")),
            max_clarify_per_finding=int(os.getenv("MAX_CLARIFY_PER_FINDING", "2")),
            max_debate_rounds=int(os.getenv("MAX_DEBATE_ROUNDS", "2")),
            max_iterations_per_checkpoint=int(os.getenv("MAX_ITERATIONS_PER_CHECKPOINT", "3")),
            max_llm_calls_total=int(os.getenv("MAX_LLM_CALLS_TOTAL", "100")),
            max_tokens_total=int(os.getenv("MAX_TOKENS_TOTAL", "500000")),
            per_agent_call_cap=int(os.getenv("PER_AGENT_CALL_CAP", "30")),
            llm_retries=int(os.getenv("LLM_RETRIES", "3")),
            llm_timeout_s=int(os.getenv("LLM_TIMEOUT_S", "60")),
            cache_dir=Path(os.getenv("ODIN_CACHE_DIR", "./data/llm_cache")),
        )
