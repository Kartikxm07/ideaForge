"""Unit tests for Phase 2: Deterministic Foundations.
Verifies citation verifier, date/SLA calculations, bad-event quarantine,
B2 incomplete status, and LLM retry/circuit breaker behavior.
"""
from datetime import date
from pathlib import Path
import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

from ragnarok.store import Store
from ragnarok.odin.config import OdinConfig
from ragnarok.odin.engine.calc import (
    load_holidays,
    add_business_days,
    month_minutes,
    uptime_percentage,
    calculate_harbor_credit,
    calculate_stratonode_credit,
    calculate_pixelwright_review_deadline,
    is_claim_time_barred,
)
from ragnarok.odin.engine.verifier import CitationVerifier
from ragnarok.odin.engine.event_parser import EventParser
from ragnarok.odin.engine.ingest import DocumentIngestor
from ragnarok.odin.engine.clock_loader import ClockLoader
from ragnarok.odin.engine.budget_guard import BudgetGuard, BudgetExceededError
from ragnarok.odin.engine.llm_client import ClaudeClient, LLMClientError
from ragnarok.odin.engine.terms_merge import TermsMergeEngine
from ragnarok.odin.bus import MessageBus


@pytest.fixture
def db_conn(tmp_path):
    db_path = tmp_path / "test_odin.sqlite3"
    store = Store(db_path)
    store.migrate()
    with store.connect() as conn:
        yield conn


@pytest.fixture
def dev_pack_dir():
    # Use canonical odin_dev_pack
    p = Path(__file__).resolve().parents[1] / "odin_dev_pack"
    assert p.exists(), f"Dev pack missing at {p}"
    return p


# 1. VERIFIER TESTS
def test_citation_verifier_accepts_verbatim_quote_and_rejects_altered_one(dev_pack_dir):
    verifier = CitationVerifier()
    a1_path = dev_pack_dir / "bundle" / "contracts" / "A1.txt"
    a1_text = a1_path.read_text(encoding="utf-8")

    # Real verbatim quote from A1.txt
    real_quote = "Monthly Fee:     $8,000.00 (Eight Thousand U.S. Dollars)"
    result = verifier.verify("A1", a1_text, real_quote, "Section C")
    assert result.verified is True
    assert result.char_start is not None

    # Normalized whitespace quote
    wrapped_quote = "Monthly Fee:\n$8,000.00 (Eight Thousand U.S. Dollars)"
    norm_result = verifier.verify("A1", a1_text, wrapped_quote, "Section C")
    assert norm_result.verified is True

    # Altered quote (e.g. changing $8,000 to $10,000)
    fake_quote = "Monthly Fee:     $10,000.00 (Ten Thousand U.S. Dollars)"
    fail_result = verifier.verify("A1", a1_text, fake_quote, "Section C")
    assert fail_result.verified is False
    assert fail_result.error is not None


# 2. CALC SLA & UPTIME TESTS
def test_calc_reproduces_march_uptime_and_credit_from_source_files():
    """Trap T2: March 3 outage (190 min).
    Harbor credit owed ($6,000), StratoNode baseline met ($0 recovery).
    """
    march_min = month_minutes(2027, 3)
    assert march_min == 44_640  # 31 days * 1440 min

    # March 3 outage duration: 190 min
    downtime = 190
    uptime = uptime_percentage(march_min, downtime)
    assert round(uptime, 2) == 99.57

    # Harbor Retail calculation (B1: 99.9% target)
    harbor = calculate_harbor_credit(downtime, month=3, year=2027, monthly_fee=40_000.0)
    assert harbor["target_met"] is False
    assert harbor["credit_percentage"] == 15.0
    assert harbor["credit_amount"] == 6_000.0

    # StratoNode calculation (A2/A3: 99.5% base target)
    strato = calculate_stratonode_credit(
        downtime_minutes=downtime,
        single_incident_max_minutes=190,
        month=3,
        year=2027,
        monthly_fee=8_000.0,
    )
    # 99.57% >= 99.50% -> Target MET!
    assert strato["target_met"] is True
    assert strato["credit_amount"] == 0.0


def test_calc_reproduces_may_uptime_and_credit_from_source_files():
    """Trap T3: May 1-2 outage (505 min).
    Harbor credit: $6,000; StratoNode recovery: $2,400 (30%); net loss: $3,600.
    """
    may_min = month_minutes(2027, 5)
    assert may_min == 44_640  # 31 days * 1440 min

    # May 1-2 outage duration: 505 min
    downtime = 505
    uptime = uptime_percentage(may_min, downtime)
    assert round(uptime, 2) == 98.87

    # Harbor Retail calculation (B1: 99.9% target)
    harbor = calculate_harbor_credit(downtime, month=5, year=2027, monthly_fee=40_000.0)
    assert harbor["target_met"] is False
    assert harbor["credit_percentage"] == 15.0
    assert harbor["credit_amount"] == 6_000.0

    # StratoNode calculation (A2 §3.1 tier 95-99% = 25% + A3 Section 2 incident >60min bonus = 5% -> 30%)
    strato = calculate_stratonode_credit(
        downtime_minutes=downtime,
        single_incident_max_minutes=505,
        month=5,
        year=2027,
        monthly_fee=8_000.0,
    )
    assert strato["target_met"] is False
    assert strato["base_credit_percentage"] == 25.0
    assert strato["incident_bonus_percentage"] == 5.0
    assert strato["total_credit_percentage"] == 30.0
    assert strato["credit_amount"] == 2_400.0

    # Net loss
    net_gap = harbor["credit_amount"] - strato["credit_amount"]
    assert net_gap == 3_600.0


# 3. DATE & HOLIDAY CALCULATION (D1 M4 REVIEW DEADLINE)
def test_calc_pixelwright_review_deadline_with_holidays(dev_pack_dir):
    """Trap T9: D1 M4 delivered 2027-04-20, 10 business-day review.
    Reject-by deadline calculated with holidays -> 2027-05-04.
    """
    holidays_file = dev_pack_dir / "bundle" / "data" / "holidays.csv"
    holidays = load_holidays(holidays_file)

    delivery_date = date(2027, 4, 20)  # Tuesday
    deadline = calculate_pixelwright_review_deadline(delivery_date, holidays, review_business_days=10)
    assert deadline == date(2027, 5, 4)  # Exactly 10 business days later


# 4. CLAIM WINDOW EXPIRATION (TIME-BARRED MARCH CLAIM)
def test_calc_harbor_march_claim_time_barred_and_may_claim_valid():
    """Trap T5: Harbor claim for March made June 15 (E-17) is time-barred under B1 45-day window.
    May claim made June 15 is valid (15 days <= 45 days).
    """
    march_end = date(2027, 3, 31)
    may_end = date(2027, 5, 31)
    claim_date = date(2027, 6, 15)

    # March: 76 days > 45 days -> time-barred
    is_barred_march, elapsed_march = is_claim_time_barred(march_end, claim_date, claim_window_days=45)
    assert is_barred_march is True
    assert elapsed_march == 76

    # May: 15 days <= 45 days -> valid
    is_barred_may, elapsed_may = is_claim_time_barred(may_end, claim_date, claim_window_days=45)
    assert is_barred_may is False
    assert elapsed_may == 15


# 5. EVENT PARSER & MALFORMED LINE QUARANTINE
def test_event_parser_quarantines_malformed_line_and_continues(db_conn, dev_pack_dir):
    """Trap T15: Drop 2 contains a deliberately malformed line on line 8.
    Must be logged and skipped; pipeline continues without crashing.
    """
    parser = EventParser(db_conn, owner_id="test-owner")

    # Drop 1: 10 valid events
    drop1_file = dev_pack_dir / "bundle" / "events" / "events_drop1.jsonl"
    res1 = parser.parse_file(drop1_file)
    assert res1["imported"] == 10
    assert res1["errors"] == 0

    # Drop 2: 8 valid events + 1 malformed line
    drop2_file = dev_pack_dir / "bundle" / "events" / "events_drop2.jsonl"
    res2 = parser.parse_file(drop2_file)
    assert res2["imported"] == 8
    assert res2["errors"] == 1
    assert len(res2["error_details"]) == 1
    assert res2["error_details"][0]["line"] == 8

    # Verify database holds quarantined error
    err_row = db_conn.execute("SELECT * FROM odin_parse_errors WHERE owner_id='test-owner'").fetchone()
    assert err_row is not None
    assert "events_drop2.jsonl:8" in err_row["source"]
    assert "malformed event line" in err_row["raw_content"]


# 6. INGEST FLAGS B2 INCOMPLETE
def test_ingest_flags_b2_incomplete_when_exhibits_missing(db_conn, dev_pack_dir):
    """Trap T16: B2 is missing exhibits; marked incomplete, flagged, no guessing."""
    ingestor = DocumentIngestor(db_conn, owner_id="test-owner")

    b2_file = dev_pack_dir / "bundle" / "contracts" / "B2.txt"
    meta_b2 = ingestor.ingest_document("B2", b2_file, "Harbor DPA")
    assert meta_b2.status == "incomplete"
    assert len(meta_b2.parse_warnings) > 0
    assert "incomplete" in meta_b2.parse_warnings[0].lower()

    # Normal contract A1 is ok
    a1_file = dev_pack_dir / "bundle" / "contracts" / "A1.txt"
    meta_a1 = ingestor.ingest_document("A1", a1_file, "StratoNode Agreement")
    assert meta_a1.status == "ok"
    assert len(meta_a1.parse_warnings) == 0


# 7. TERMS MERGE & SUPERSEDING AMENDMENTS
def test_terms_merge_applies_a3_overrides_to_a2(db_conn):
    """Trap T4: A3 silently shortens StratoNode claim window to 15 days
    and changes non-renewal notice to 60 days.
    """
    engine = TermsMergeEngine(db_conn, owner_id="test-owner")

    base_terms = [
        {
            "doc_id": "A2",
            "term_key": "claim_window_days",
            "value": "30",
            "citations": [{"doc_id": "A2", "clause_ref": "§3.2", "quote": "within thirty (30) days"}],
            "note": "Base SLA claim window",
        },
        {
            "doc_id": "A2",
            "term_key": "non_renewal_notice_days",
            "value": "90",
            "citations": [{"doc_id": "A1", "clause_ref": "Section B", "quote": "ninety (90) days"}],
            "note": "Original Cover Page notice",
        },
    ]

    amendments = [
        {
            "target_doc_id": "A2",
            "term_key": "claim_window_days",
            "amd_doc_id": "A3",
            "new_value": "15",
            "citations": [{"doc_id": "A3", "clause_ref": "Section 1 (§3.2)", "quote": "within fifteen (15) days"}],
            "note": "A3 Section 1 replaces A2 Section 3.2",
        },
        {
            "target_doc_id": "A2",
            "term_key": "non_renewal_notice_days",
            "amd_doc_id": "A3",
            "new_value": "60",
            "citations": [{"doc_id": "A3", "clause_ref": "Section 3", "quote": "sixty (60) days"}],
            "note": "A3 Section 3 amends Section B",
        },
    ]

    effective = engine.merge_terms(base_terms, amendments)
    eff_map = {t.term_key: t for t in effective}

    assert eff_map["claim_window_days"].value == "15"
    assert eff_map["claim_window_days"].superseded_by == "A3"
    assert len(eff_map["claim_window_days"].derived_from) == 2  # Both citations preserved

    assert eff_map["non_renewal_notice_days"].value == "60"
    assert eff_map["non_renewal_notice_days"].superseded_by == "A3"


# 8. BUDGET GUARD & CIRCUIT BREAKER
def test_budget_guard_trips_circuit_breaker():
    guard = BudgetGuard(max_total_calls=2, per_agent_call_cap=2)
    guard.check_can_call("thor")
    guard.record_usage("thor", tokens_in=100, tokens_out=50)

    guard.check_can_call("thor")
    guard.record_usage("thor", tokens_in=100, tokens_out=50)

    # 3rd call must trip circuit breaker
    with pytest.raises(BudgetExceededError):
        guard.check_can_call("thor")


# 9. LLM RETRY, CACHING & FALLBACK
class SampleOutput(BaseModel):
    summary: str
    confidence: float


def test_mocked_llm_failure_triggers_retry_and_caching(tmp_path, db_conn):
    guard = BudgetGuard()
    client = ClaudeClient(
        api_key="mock-api-key",
        budget_guard=guard,
        db=db_conn,
        owner_id="test-owner",
        cache_dir=tmp_path / "cache",
        max_retries=2,
    )

    # Mock client messages.create to fail on first attempt, then succeed on second attempt
    mock_messages = MagicMock()
    success_resp = MagicMock()
    success_resp.content = [MagicMock(text='{"summary": "Test Contract Summary", "confidence": 0.95}')]
    success_resp.usage = MagicMock(input_tokens=50, output_tokens=25)

    mock_messages.create.side_effect = [
        Exception("Temporary API connection timeout"),
        success_resp,
    ]
    client._anthropic_client = MagicMock(messages=mock_messages)

    result = client.call_structured(
        agent="thor",
        model="claude-3-5-haiku-20241022",
        system_prompt="Extract terms",
        user_prompt="Analyze A1",
        response_model=SampleOutput,
    )

    assert result.summary == "Test Contract Summary"
    assert result.confidence == 0.95
    assert mock_messages.create.call_count == 2  # Failed once, succeeded on retry
    assert guard.total_calls == 1

    # Second identical call should hit cache and NOT invoke messages.create again
    cached_result = client.call_structured(
        agent="thor",
        model="claude-3-5-haiku-20241022",
        system_prompt="Extract terms",
        user_prompt="Analyze A1",
        response_model=SampleOutput,
    )
    assert cached_result.summary == "Test Contract Summary"
    assert mock_messages.create.call_count == 2  # Still 2, cached hit!


# 10. CLOCK LOADER
def test_clock_loader_and_checkpoint_events(dev_pack_dir):
    clock_file = dev_pack_dir / "clock.json"
    loader = ClockLoader(clock_file)
    assert loader.start_date == "2027-01-15"
    assert loader.checkpoints == ["2027-03-15", "2027-06-01", "2027-09-15"]

    assert loader.is_event_prior_to_checkpoint("2027-01-22T09:30:00Z", "2027-03-15") is True
    assert loader.is_event_prior_to_checkpoint("2027-04-20T10:00:00Z", "2027-03-15") is False
    assert loader.is_event_prior_to_checkpoint("2027-04-20T10:00:00Z", "2027-06-01") is True


# 11. MESSAGE BUS
def test_message_bus_logs_and_persists_envelopes(db_conn):
    bus = MessageBus(db_conn, owner_id="test-owner")
    env = bus.emit(
        from_agent="loki",
        to_agent="heimdall_2",
        msg_type="propose_finding",
        payload_ref="F-001",
        clock_t="2027-03-15",
    )
    assert env.msg_id.startswith("msg-")
    assert env.from_agent == "loki"
    assert env.clock_t == "2027-03-15"

    messages = bus.get_messages(clock_t="2027-03-15")
    assert len(messages) == 1
    assert messages[0].payload_ref == "F-001"

    row = db_conn.execute("SELECT * FROM odin_messages WHERE msg_id=?", (env.msg_id,)).fetchone()
    assert row is not None
    assert row["from_agent"] == "loki"
