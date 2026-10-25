"""Message and Telemetry Event Bus.
Implements the agent-to-agent transition log and hand-off bus.
"""
from dataclasses import dataclass, field
import sqlite3
from typing import Optional
import uuid
from ..store import now
from .models import MessageEnvelope


class MessageBus:
    """Dispatches and persists messages between Odin agents."""

    def __init__(self, db: sqlite3.Connection, owner_id: str):
        self.db = db
        self.owner_id = owner_id
        self._in_memory_log: list[MessageEnvelope] = []

    def emit(
        self,
        from_agent: str,
        to_agent: str,
        msg_type: str,
        payload_ref: Optional[str] = None,
        clock_t: Optional[str] = None,
    ) -> MessageEnvelope:
        """Emit a typed message envelope, append to log, and persist in SQLite."""
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"
        ts = now()
        envelope = MessageEnvelope(
            msg_id=msg_id,
            from_agent=from_agent,
            to_agent=to_agent,
            type=msg_type,
            payload_ref=payload_ref,
            clock_t=clock_t,
            timestamp=ts,
        )

        self._in_memory_log.append(envelope)

        self.db.execute(
            """
            INSERT INTO odin_messages(msg_id, owner_id, from_agent, to_agent, type, payload_ref, clock_t, timestamp)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg_id,
                self.owner_id,
                from_agent,
                to_agent,
                msg_type,
                payload_ref,
                clock_t,
                ts,
            ),
        )

        return envelope

    def get_messages(self, clock_t: Optional[str] = None) -> list[MessageEnvelope]:
        """Fetch logged messages, optionally filtered by clock checkpoint."""
        if clock_t:
            return [m for m in self._in_memory_log if m.clock_t == clock_t]
        return list(self._in_memory_log)
