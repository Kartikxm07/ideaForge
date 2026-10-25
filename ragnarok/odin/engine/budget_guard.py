"""Budget Guard & Circuit Breaker.
Tracks LLM calls and token expenditure across agents, tripping circuit breakers
before exceeding configured limits.
"""
from dataclasses import dataclass, field
import threading
from typing import Optional


class BudgetExceededError(RuntimeError):
    """Raised when an execution loop or agent exceeds configured resource limits."""
    pass


@dataclass
class BudgetGuard:
    max_total_calls: int = 100
    max_total_tokens: int = 500_000
    per_agent_call_cap: int = 30

    total_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    calls_by_agent: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check_can_call(self, agent: str, estimated_tokens: int = 0) -> None:
        """Verify that an upcoming agent invocation is within budget limits."""
        with self._lock:
            if self.total_calls >= self.max_total_calls:
                raise BudgetExceededError(
                    f"Global LLM call limit reached ({self.total_calls}/{self.max_total_calls})"
                )

            total_tokens = self.total_tokens_in + self.total_tokens_out + estimated_tokens
            if total_tokens > self.max_total_tokens:
                raise BudgetExceededError(
                    f"Global token budget exceeded ({total_tokens}/{self.max_total_tokens})"
                )

            agent_calls = self.calls_by_agent.get(agent, 0)
            if agent_calls >= self.per_agent_call_cap:
                raise BudgetExceededError(
                    f"Agent '{agent}' hit call cap ({agent_calls}/{self.per_agent_call_cap})"
                )

    def record_usage(self, agent: str, tokens_in: int, tokens_out: int) -> None:
        """Record completed LLM usage."""
        with self._lock:
            self.total_calls += 1
            self.total_tokens_in += tokens_in
            self.total_tokens_out += tokens_out
            self.calls_by_agent[agent] = self.calls_by_agent.get(agent, 0) + 1

    def get_summary(self) -> dict:
        """Return current budget utilization."""
        with self._lock:
            return {
                "total_calls": self.total_calls,
                "max_total_calls": self.max_total_calls,
                "total_tokens": self.total_tokens_in + self.total_tokens_out,
                "max_total_tokens": self.max_total_tokens,
                "tokens_in": self.total_tokens_in,
                "tokens_out": self.total_tokens_out,
                "calls_by_agent": dict(self.calls_by_agent),
            }
