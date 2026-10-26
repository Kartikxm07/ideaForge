"""
ragnarok/norns_finance.py
─────────────────────────
Norns Financial Exposure Engine.

Converts contract clause extractions + payment ledger data into
worst-case dollar projections. Handles both explicit ISO dates AND
relative time expressions ("30 days prior to renewal",
"auto-renews annually unless cancelled 60 days prior").

Deterministic clause arithmetic only — zero LLM calls.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, timedelta

# ── Default rates from Odin dev-pack contracts ────────────────────────
DEFAULT_MONTHLY_INTEREST = 0.015  # Section C: 1.5%/month late payment
DEFAULT_RENEWAL_MONTHS   = 12     # Standard successive renewal period
DEFAULT_NOTICE_DAYS      = 90     # Standard non-renewal notice window

# ── Regex patterns ─────────────────────────────────────────────────────
_MONEY_RE       = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)", re.I)
_PCTPM_RE       = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:per\s+month|monthly|p\.?m\.?)", re.I)
_DAYS_BEFORE_RE = re.compile(r"(\d+)\s+days?\s+(?:prior|before|in\s+advance)", re.I)
_DAYS_AFTER_RE  = re.compile(r"(\d+)\s+days?\s+(?:after|post|following)", re.I)
_WITHIN_RE      = re.compile(r"within\s+(\d+)\s+(?:calendar\s+)?days?", re.I)
_RENEWAL_MO_RE  = re.compile(r"successive\s+(\d+).month|(\d+).month\s+(?:renewal|period|term)", re.I)
_CREDIT_PCT_RE  = re.compile(r"(\d+)\s*%\s*(?:of\s+(?:the\s+)?monthly\s+(?:fee|fees)|credit)", re.I)
_AUTO_RENEW_RE  = re.compile(r"auto.?renew|successive\s+\w+\s+period", re.I)
_WORD_DAYS: dict[str, int] = {
    "thirty": 30, "sixty": 60, "ninety": 90,
    "one hundred twenty": 120, "fourteen": 14, "seven": 7,
}


@dataclass
class Milestone:
    """One financial or procedural milestone in the worst-case timeline."""
    milestone_id: str
    date: str               # ISO YYYY-MM-DD
    clause_citation: str
    event_type: str         # RENEWAL_WINDOW | PAYMENT_DUE | SLA_AUDIT | TERMINATION_NOTICE
    description: str
    worst_case_usd: float
    formula: str
    risk_severity: str      # CRITICAL | HIGH | MEDIUM | LOW
    document_key: str = ""
    source_tag: str = "computed"


# ── Helpers ────────────────────────────────────────────────────────────

def _money(text: str) -> float:
    m = _MONEY_RE.search(text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _monthly_rate(text: str) -> float:
    m = _PCTPM_RE.search(text)
    return float(m.group(1)) / 100.0 if m else DEFAULT_MONTHLY_INTEREST


def _parse_days(text: str) -> int:
    """Parse a day count from phrases like '30 days', 'ninety days', '3 months'."""
    tl = text.lower()
    for word, num in _WORD_DAYS.items():
        if word in tl:
            return num
    m_mo = re.search(r"(\d+)\s+months?", tl)
    if m_mo:
        return int(m_mo.group(1)) * 30
    m_yr = re.search(r"(\d+)\s+years?", tl)
    if m_yr:
        return int(m_yr.group(1)) * 365
    m_d = re.search(r"(\d+)\s+(?:business\s+)?days?", tl)
    if m_d:
        return int(m_d.group(1))
    return 0


def parse_ledger(csv_text: str) -> list[dict]:
    """Parse a CSV ledger string into row dicts."""
    try:
        return [dict(r) for r in csv.DictReader(io.StringIO(csv_text.strip()))]
    except Exception:
        return []


parse_relative_days = _parse_days
TimelineMilestone = Milestone


# ── Main calculation ───────────────────────────────────────────────────

def compute_exposure(
    extractions: list[dict],
    ledger_rows: list[dict],
    clock_t: str,
    doc_key: str = "",
) -> tuple[list[Milestone], float]:
    """
    Compute worst-case financial milestones.

    Parameters
    ----------
    extractions  : agent-extraction dicts from the Thor node.
    ledger_rows  : Payment ledger rows from CSV.
    clock_t      : ISO date string — simulated "now" for this checkpoint.
    doc_key      : Fallback document key.

    Returns
    -------
    (milestones, total_worst_case_usd)
    """
    try:
        clock = date.fromisoformat(clock_t)
    except (ValueError, TypeError):
        clock = date.today()

    milestones: list[Milestone] = []
    _mid = [1]

    def _next_id() -> str:
        _id = f"MS-{_mid[0]:03d}"
        _mid[0] += 1
        return _id

    # ── 1. Payment ledger: overdue / pending ──────────────────────────
    monthly_contracted = 0.0
    overdue: list[dict] = []

    for row in ledger_rows:
        try:
            pdate  = date.fromisoformat(row.get("date", ""))
            amount = float(row.get("amount", 0))
            status = row.get("status", "").lower()
            if status == "cleared":
                if amount > monthly_contracted:
                    monthly_contracted = amount
            elif status in ("pending", "overdue", "late", "unpaid"):
                if pdate <= clock:
                    overdue.append({
                        "date": pdate, "amount": amount,
                        "ref": row.get("reference", "?"),
                        "to":  row.get("to", "counterparty"),
                    })
        except (ValueError, TypeError):
            continue

    for ov in overdue:
        days_late   = max(0, (clock - ov["date"]).days)
        months_late = max(1, days_late // 30)
        interest    = ov["amount"] * DEFAULT_MONTHLY_INTEREST * months_late
        milestones.append(Milestone(
            milestone_id=_next_id(),
            date=ov["date"].isoformat(),
            clause_citation="Section C — Fees and Payment",
            event_type="PAYMENT_DUE",
            description=(
                f"Overdue payment {ov['ref']} to {ov['to']} — "
                f"{days_late} days late ({months_late} billing period(s))"
            ),
            worst_case_usd=ov["amount"] + interest,
            formula=(
                f"${ov['amount']:,.2f} principal + ${interest:,.2f} interest "
                f"({DEFAULT_MONTHLY_INTEREST*100:.1f}%/mo x {months_late} mo)"
            ),
            risk_severity="CRITICAL" if interest > 2_000 else "HIGH",
            document_key=doc_key,
        ))

    # ── 2. Infer monthly fee from extractions when ledger is absent ───
    if monthly_contracted == 0.0:
        for ex in extractions:
            combined = f"{ex.get('value', '')} {ex.get('citation', {}).get('quote', '')}"
            amt = _money(combined)
            if amt > 0 and "month" in combined.lower():
                monthly_contracted = amt
                break

    # ── 3. Clause-level milestones ────────────────────────────────────
    for ex in extractions:
        field_name = ex.get("field", "")
        quote  = ex.get("citation", {}).get("quote", "") or ""
        value  = ex.get("value", "") or ""
        clause = ex.get("citation", {}).get("clause_ref", "") or field_name
        dk     = ex.get("document_key", doc_key)
        combined = f"{quote} {value}"

        # Renewal window
        if field_name in ("dates", "termination") or _AUTO_RENEW_RE.search(combined):
            m_notice = _DAYS_BEFORE_RE.search(combined)
            m_period = _RENEWAL_MO_RE.search(combined)
            notice_days    = int(m_notice.group(1)) if m_notice else DEFAULT_NOTICE_DAYS
            raw_period = (m_period.group(1) or m_period.group(2)) if m_period else None
            renewal_months = int(raw_period) if raw_period else DEFAULT_RENEWAL_MONTHS
            fee = monthly_contracted or _money(combined)
            if fee > 0:
                deadline = clock - timedelta(days=notice_days)
                exposure = fee * renewal_months
                milestones.append(Milestone(
                    milestone_id=_next_id(),
                    date=deadline.isoformat(),
                    clause_citation=clause,
                    event_type="RENEWAL_WINDOW",
                    description=(
                        f"Non-renewal notice must be dispatched >= {notice_days} days "
                        f"before renewal. Missed window locks in {renewal_months}-month term."
                    ),
                    worst_case_usd=exposure,
                    formula=f"${fee:,.2f}/mo x {renewal_months} mo = ${exposure:,.2f}",
                    risk_severity="CRITICAL" if exposure > 50_000 else "HIGH",
                    document_key=dk,
                ))

        # Late-payment interest
        if any(kw in combined.lower() for kw in ("interest", "overdue", "accrues", "accrue")):
            rate = _monthly_rate(combined)
            base = _money(combined) or monthly_contracted
            if base > 0 and rate > 0:
                monthly_charge = base * rate
                milestones.append(Milestone(
                    milestone_id=_next_id(),
                    date=clock.isoformat(),
                    clause_citation=clause,
                    event_type="PAYMENT_DUE",
                    description=f"Recurring monthly interest on outstanding balance ({rate*100:.1f}%/mo on ${base:,.2f})",
                    worst_case_usd=monthly_charge,
                    formula=f"${base:,.2f} x {rate*100:.1f}% = ${monthly_charge:,.2f}/mo",
                    risk_severity="HIGH" if monthly_charge > 500 else "MEDIUM",
                    document_key=dk,
                ))

        # SLA credit tiers
        if field_name in ("sla_tier", "credit_tiers") or ("credit" in combined.lower() and "%" in combined):
            m_pct = _CREDIT_PCT_RE.search(combined)
            if m_pct:
                pct = float(m_pct.group(1)) / 100.0
                fee = monthly_contracted or 8_000.0
                credit_usd = fee * pct
                milestones.append(Milestone(
                    milestone_id=_next_id(),
                    date=clock.isoformat(),
                    clause_citation=clause,
                    event_type="SLA_AUDIT",
                    description=(
                        f"Max SLA service credit if performance drops below threshold "
                        f"({pct*100:.0f}% of monthly fee = ${credit_usd:,.2f})"
                    ),
                    worst_case_usd=credit_usd,
                    formula=f"${fee:,.2f}/mo x {pct*100:.0f}% = ${credit_usd:,.2f}",
                    risk_severity="MEDIUM",
                    document_key=dk,
                ))

        # Termination / notice windows (relative)
        if field_name in ("termination", "notice_terms") or "terminat" in combined.lower():
            m_win = _WITHIN_RE.search(combined) or _DAYS_AFTER_RE.search(combined)
            if m_win:
                days = int(m_win.group(1))
                deadline = clock + timedelta(days=days)
                milestones.append(Milestone(
                    milestone_id=_next_id(),
                    date=deadline.isoformat(),
                    clause_citation=clause,
                    event_type="TERMINATION_NOTICE",
                    description=f"Termination notice window — action required within {days} days",
                    worst_case_usd=0.0,
                    formula=f"Procedural deadline: {days} calendar days from {clock_t}",
                    risk_severity="HIGH",
                    document_key=dk,
                ))

    # ── 4. De-duplicate: keep highest exposure per event_type+date ────
    dedup: dict[str, Milestone] = {}
    for ms in milestones:
        key = f"{ms.event_type}:{ms.date}"
        if key not in dedup or ms.worst_case_usd > dedup[key].worst_case_usd:
            dedup[key] = ms

    final = sorted(dedup.values(), key=lambda m: m.date)
    total = sum(m.worst_case_usd for m in final)
    return final, total
