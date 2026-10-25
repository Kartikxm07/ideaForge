"""Deterministic Calculation Engine.
Math and dates are done strictly in code, not by LLMs.
Handles business days with holidays, month minute totals, uptime %, SLA credit tiers,
claim window expirations, and financial recovery calculations.
"""
import calendar
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Set, Union


def parse_date(d: Union[str, date, datetime]) -> date:
    """Parse string or datetime into a date object."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    # String format parsing (YYYY-MM-DD or ISO timestamp)
    clean_str = d.split("T")[0].strip()
    return datetime.strptime(clean_str, "%Y-%m-%d").date()


def load_holidays(holidays_csv_path: Union[Path, str]) -> Set[date]:
    """Load observed holidays from holidays.csv into a set of date objects."""
    p = Path(holidays_csv_path)
    if not p.exists():
        return set()

    holidays: Set[date] = set()
    with open(p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_str = row.get("date", "").strip()
            if d_str:
                try:
                    holidays.add(parse_date(d_str))
                except ValueError:
                    continue
    return holidays


def is_business_day(d: date, holidays: Set[date]) -> bool:
    """Return True if date is a weekday (Monday-Friday) and not an observed holiday."""
    if d.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    return d not in holidays


def add_business_days(start_date: Union[str, date], n_days: int, holidays: Set[date]) -> date:
    """Calculate the date that is n business days after start_date.
    Per standard contract procedure, day 1 is the first business day following start_date.
    """
    curr = parse_date(start_date)
    added = 0
    while added < n_days:
        curr += timedelta(days=1)
        if is_business_day(curr, holidays):
            added += 1
    return curr


def days_between(d1: Union[str, date], d2: Union[str, date]) -> int:
    """Return integer calendar days between d1 and d2 (d2 - d1)."""
    return (parse_date(d2) - parse_date(d1)).days


def add_calendar_days(d: Union[str, date], days: int) -> date:
    """Add calendar days to date."""
    return parse_date(d) + timedelta(days=days)


def month_minutes(year: int, month: int) -> int:
    """Return total minutes in a given calendar month."""
    _, num_days = calendar.monthrange(year, month)
    return num_days * 24 * 60


def uptime_percentage(total_minutes: int, downtime_minutes: int) -> float:
    """Calculate Monthly Uptime Percentage: (total - downtime) / total * 100."""
    if total_minutes <= 0:
        return 0.0
    val = ((total_minutes - downtime_minutes) / total_minutes) * 100.0
    return round(val, 4)


def calculate_harbor_credit(
    downtime_minutes: int,
    month: int,
    year: int,
    monthly_fee: float = 40_000.0,
) -> dict[str, Any]:
    """Calculate Harbor Retail SLA credit under Contract B1 §3.
    - Uptime Target: 99.9%
    - Credit: 15% of Monthly Fee if uptime < 99.9% (§3.3)
    - Cap: 20% of Monthly Fee (§3.4)
    """
    total_min = month_minutes(year, month)
    uptime_pct = uptime_percentage(total_min, downtime_minutes)
    target_met = uptime_pct >= 99.9

    if target_met:
        credit_pct = 0.0
        credit_amount = 0.0
    else:
        credit_pct = 15.0
        credit_amount = monthly_fee * (credit_pct / 100.0)
        # Cap check (20%)
        max_credit = monthly_fee * 0.20
        credit_amount = min(credit_amount, max_credit)

    return {
        "contract_id": "B1",
        "month": month,
        "year": year,
        "total_minutes": total_min,
        "downtime_minutes": downtime_minutes,
        "uptime_percentage": uptime_pct,
        "uptime_target": 99.9,
        "target_met": target_met,
        "credit_percentage": credit_pct,
        "credit_amount": round(credit_amount, 2),
        "monthly_fee": monthly_fee,
        "clause_ref": "B1 §3.3",
    }


def calculate_stratonode_credit(
    downtime_minutes: int,
    single_incident_max_minutes: int,
    month: int,
    year: int,
    monthly_fee: float = 8_000.0,
) -> dict[str, Any]:
    """Calculate StratoNode SLA credit under A2 (SLA) as amended by A3 (Amendment No. 1).
    - Base Target: 99.5%
    - Tiers (A3 Section 2):
        99.0% to < 99.5%: 10%
        95.0% to < 99.0%: 25%
        Below 95.0%: 50%
    - Plus 5% if single incident > 60 consecutive minutes (A3 Section 2)
    - Max cap: 50%
    """
    total_min = month_minutes(year, month)
    uptime_pct = uptime_percentage(total_min, downtime_minutes)
    target_met = uptime_pct >= 99.5

    if target_met:
        base_credit_pct = 0.0
    elif uptime_pct >= 99.0:
        base_credit_pct = 10.0
    elif uptime_pct >= 95.0:
        base_credit_pct = 25.0
    else:
        base_credit_pct = 50.0

    # Incident bonus (A3 Section 2): 5% if single incident exceeds 60 minutes
    incident_bonus_pct = 5.0 if (not target_met and single_incident_max_minutes > 60) else 0.0

    total_credit_pct = min(base_credit_pct + incident_bonus_pct, 50.0)
    credit_amount = monthly_fee * (total_credit_pct / 100.0)

    return {
        "contract_id": "A2/A3",
        "month": month,
        "year": year,
        "total_minutes": total_min,
        "downtime_minutes": downtime_minutes,
        "single_incident_max_minutes": single_incident_max_minutes,
        "uptime_percentage": uptime_pct,
        "uptime_target": 99.5,
        "target_met": target_met,
        "base_credit_percentage": base_credit_pct,
        "incident_bonus_percentage": incident_bonus_pct,
        "total_credit_percentage": total_credit_pct,
        "credit_amount": round(credit_amount, 2),
        "monthly_fee": monthly_fee,
        "clause_ref": "A2 §3.1 & A3 Section 2",
    }


def calculate_pixelwright_review_deadline(
    delivery_date: Union[str, date],
    holidays: Set[date],
    review_business_days: int = 10,
) -> date:
    """Under D1 §4.2, review period is 10 business days after receipt."""
    return add_business_days(delivery_date, review_business_days, holidays)


def is_claim_time_barred(
    incident_month_end_date: Union[str, date],
    claim_submission_date: Union[str, date],
    claim_window_days: int,
) -> tuple[bool, int]:
    """Check if a claim submission date exceeds the claim window after the incident month end.
    Returns (is_time_barred, elapsed_days).
    """
    elapsed = days_between(incident_month_end_date, claim_submission_date)
    return (elapsed > claim_window_days, elapsed)
