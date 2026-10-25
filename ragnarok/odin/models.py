"""Pydantic models for ODIN structured state and data transfer."""
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str
    clause_ref: str
    quote: str


class DocumentMetadata(BaseModel):
    doc_id: str
    path: str
    title: str
    status: Literal["ok", "incomplete", "malformed"] = "ok"
    parse_warnings: list[str] = Field(default_factory=list)
    clause_count: int = 0


class ClauseItem(BaseModel):
    clause_id: str
    doc_id: str
    section_ref: str
    heading: str
    body: str
    char_offset_start: Optional[int] = None
    char_offset_end: Optional[int] = None


class ExtractionItem(BaseModel):
    ext_id: str
    doc_id: str
    field: str
    value: str
    clause_ref: str
    quote: str
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguity_flag: bool = False
    ambiguity_note: Optional[str] = None
    source_tag: Literal["sourced", "inferred"] = "sourced"


class EffectiveTerm(BaseModel):
    term_id: str
    doc_id: str
    term_key: str
    value: str
    derived_from: list[Citation] = Field(default_factory=list)
    superseded_by: Optional[str] = None
    note: Optional[str] = None


class OperationalEvent(BaseModel):
    event_id: str
    timestamp: str
    channel: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: str
    raw_json: Optional[str] = None


class EventMapping(BaseModel):
    map_id: str
    event_id: str
    doc_id: Optional[str] = None
    clause_ref: Optional[str] = None
    relevance: Literal["action", "info", "noise"] = "info"
    reasoning: Optional[str] = None
    valid_notice: Optional[bool] = None


class AlertItem(BaseModel):
    alert_id: str
    clock_t: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    type: Literal["deadline", "renewal", "payment", "breach", "other"]
    doc_id: str
    clause_ref: Optional[str] = None
    message: str
    due_date: Optional[str] = None
    event_ids: list[str] = Field(default_factory=list)
    acknowledged: bool = False


class TimelineItem(BaseModel):
    timeline_id: str
    clock_t: str
    doc_id: str
    item_type: Literal["past", "due_now", "upcoming", "penalty_trigger", "missed"]
    date: str
    description: str
    amount: Optional[float] = None
    citation: Optional[Citation] = None
    status: Optional[str] = None


class ExposureItem(BaseModel):
    exposure_id: str
    clock_t: str
    doc_id: str
    scenario: Literal["expected", "worst_case"]
    amount: float
    breakdown: Optional[dict[str, Any]] = None
    formula: Optional[str] = None


class FindingItem(BaseModel):
    finding_id: str
    clock_t: str
    source_agent: str = "loki"
    docs: list[str]
    citations: list[Citation]
    attack_path: list[str]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    likelihood: float = Field(ge=0.0, le=1.0)
    tag: Literal["sourced", "inferred"]
    status: Literal["proposed", "confirmed", "challenged", "noise", "ruled", "closed"] = "proposed"


class ClarificationItem(BaseModel):
    req_id: str
    finding_id: str
    doc_id: str
    clause_ref: str
    question: str
    answer: Optional[str] = None
    round: int = 1


class VerificationItem(BaseModel):
    verif_id: str
    finding_id: str
    verdict: Literal["confirmed", "challenged", "noise"]
    reasons: list[str]
    event_ids: list[str] = Field(default_factory=list)
    clause_checks: Optional[dict[str, Any]] = None
    recomputed_numbers: Optional[dict[str, Any]] = None


class RulingItem(BaseModel):
    ruling_id: str
    finding_id: str
    outcome: Literal["upheld", "rejected", "partial"]
    rationale: str
    citations: list[Citation] = Field(default_factory=list)
    round: int = 1


class ActionItem(BaseModel):
    action_id: str
    finding_id: Optional[str] = None
    type: Literal["renewal", "termination", "breach", "cure", "rejection", "amendment", "escalation"]
    recipient: str
    recipient_address: str
    signer: str
    subject: str
    body: str
    citations: list[Citation]
    deadline: str
    confidence: float
    needs_human_approval: bool = True
    status: Literal["draft_pending_approval", "approved", "rejected"] = "draft_pending_approval"


class MessageEnvelope(BaseModel):
    msg_id: str
    from_agent: str
    to_agent: str
    type: str
    payload_ref: Optional[str] = None
    clock_t: Optional[str] = None
    timestamp: str


class ClockSpec(BaseModel):
    start_date: str
    checkpoints: list[str]
