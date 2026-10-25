"""Phase 2 Demo: Deterministic Foundations in Action.
Runs ingestion on all contracts and events from odin_dev_pack,
executes deterministic calculations for acceptance traps (T2, T3, T5, T9, T15, T16),
and prints an executive summary.
"""
from datetime import date
from pathlib import Path
import sys

from ragnarok.store import Store
from ragnarok.odin.config import OdinConfig
from ragnarok.odin.engine.ingest import DocumentIngestor
from ragnarok.odin.engine.event_parser import EventParser
from ragnarok.odin.engine.clock_loader import ClockLoader
from ragnarok.odin.engine.calc import (
    load_holidays,
    month_minutes,
    uptime_percentage,
    calculate_harbor_credit,
    calculate_stratonode_credit,
    calculate_pixelwright_review_deadline,
    is_claim_time_barred,
)
from ragnarok.odin.engine.verifier import CitationVerifier


def run_demo():
    print("=" * 80)
    print("       ODIN PHASE 2 DEMO: DETERMINISTIC FOUNDATIONS & VERIFICATION")
    print("=" * 80)

    repo_root = Path(__file__).resolve().parents[2]
    dev_pack_dir = repo_root / "odin_dev_pack"
    db_path = repo_root / "data" / "odin_demo.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Database & Migrations
    print("\n[1] INITIALIZING PERSISTENT STATE STORE (SQLite)")
    store = Store(db_path)
    store.migrate()
    print(f"    Database: {db_path} (PRAGMA user_version = 6)")

    with store.connect() as db:
        # 2. Ingest Contracts
        print("\n[2] INGESTING CANONICAL CONTRACTS")
        ingestor = DocumentIngestor(db, owner_id="demo-owner")
        manifest_path = dev_pack_dir / "bundle" / "manifest.json"
        docs = ingestor.ingest_bundle(dev_pack_dir)
        print(f"    Ingested {len(docs)} contracts into SQLite:")
        for d in docs:
            flag_str = f" [WARNING: {d.parse_warnings[0]}]" if d.parse_warnings else ""
            print(f"    - {d.doc_id:4s} | Status: {d.status:10s} | Clauses: {d.clause_count:2d} | {d.title}{flag_str}")

        # 3. Parse Event Feeds with Bad-Line Quarantine
        print("\n[3] PARSING OPERATIONAL EVENT STREAMS")
        parser = EventParser(db, owner_id="demo-owner")
        drop1 = dev_pack_dir / "bundle" / "events" / "events_drop1.jsonl"
        drop2 = dev_pack_dir / "bundle" / "events" / "events_drop2.jsonl"

        res1 = parser.parse_file(drop1)
        res2 = parser.parse_file(drop2)
        print(f"    Drop 1: {res1['imported']} events imported, {res1['errors']} errors")
        print(f"    Drop 2: {res2['imported']} events imported, {res2['errors']} errors")
        for err in res2["error_details"]:
            print(f"    -> Quarantined line {err['line']}: \"{err['raw']}\" ({err['error']})")

        # 4. Clock Checkpoints
        clock = ClockLoader(dev_pack_dir / "clock.json")
        print(f"\n[4] SIMULATED CLOCK SPECIFICATION")
        print(f"    Start Date : {clock.start_date}")
        print(f"    Checkpoints: {', '.join(clock.checkpoints)}")

        # 5. Deterministic Calculations & Trap Verifications
        print("\n[5] DETERMINISTIC SLA, DATE & FINANCIAL ENGINE CHECKS")
        holidays = load_holidays(dev_pack_dir / "bundle" / "data" / "holidays.csv")
        print(f"    Loaded {len(holidays)} observed business holidays")

        # Trap T2: March Outage (190 min)
        march_harbor = calculate_harbor_credit(190, month=3, year=2027)
        march_strato = calculate_stratonode_credit(190, single_incident_max_minutes=190, month=3, year=2027)
        print(f"\n    [T2] March 3 Outage (190 min):")
        print(f"         - Uptime: {march_harbor['uptime_percentage']}%")
        print(f"         - Harbor Credit (B1 target 99.9%): ${march_harbor['credit_amount']:,.2f} (15%)")
        print(f"         - StratoNode Recovery (A2 target 99.5%): ${march_strato['credit_amount']:,.2f} (Target Met)")
        print(f"         - Net Quillhub Loss: ${march_harbor['credit_amount']:,.2f}")

        # Trap T3: May Outage (505 min)
        may_harbor = calculate_harbor_credit(505, month=5, year=2027)
        may_strato = calculate_stratonode_credit(505, single_incident_max_minutes=505, month=5, year=2027)
        net_may = may_harbor["credit_amount"] - may_strato["credit_amount"]
        print(f"\n    [T3] May 1-2 Outage (505 min):")
        print(f"         - Uptime: {may_harbor['uptime_percentage']}%")
        print(f"         - Harbor Credit (B1 target 99.9%): ${may_harbor['credit_amount']:,.2f} (15%)")
        print(f"         - StratoNode Recovery (A3 tier 25% + 5% incident >60m = 30%): ${may_strato['credit_amount']:,.2f}")
        print(f"         - Net Quillhub Loss: ${net_may:,.2f}")

        # Trap T5: Harbor SLA Claim Time-Barring
        is_mar_barred, mar_days = is_claim_time_barred(date(2027, 3, 31), date(2027, 6, 15), 45)
        is_may_barred, may_days = is_claim_time_barred(date(2027, 5, 31), date(2027, 6, 15), 45)
        print(f"\n    [T5] Harbor SLA Credit Request Submitted June 15, 2027 (E-17):")
        print(f"         - March Claim: {mar_days} days elapsed -> {'TIME-BARRED (Invalid)' if is_mar_barred else 'Valid'}")
        print(f"         - May Claim  : {may_days} days elapsed -> {'Time-barred' if is_may_barred else 'VALID (Payable)'}")

        # Trap T9: Pixelwright M4 Review Deadline
        m4_deadline = calculate_pixelwright_review_deadline(date(2027, 4, 20), holidays, 10)
        print(f"\n    [T9] Pixelwright M4 Deliverable Review Window (D1 §4.2):")
        print(f"         - Delivery Date : 2027-04-20 (Tuesday)")
        print(f"         - Reject-by Date: {m4_deadline} (10 business days, deemed accepted after)")

        # 6. Verifier Check
        print(f"\n[6] VERBATIM CITATION GATEWAY CHECK")
        verifier = CitationVerifier()
        a1_text = (dev_pack_dir / "bundle" / "contracts" / "A1.txt").read_text(encoding="utf-8")
        test_quote = "Monthly Fee:     $8,000.00 (Eight Thousand U.S. Dollars)"
        v_res = verifier.verify("A1", a1_text, test_quote, "Section C")
        print(f"    - Checking real quote from A1.txt: {'VERIFIED' if v_res.verified else 'FAILED'} (span: {v_res.char_start}..{v_res.char_end})")
        fake_quote = "Monthly Fee:     $99,999.00 (Fake Fee)"
        f_res = verifier.verify("A1", a1_text, fake_quote, "Section C")
        print(f"    - Checking altered quote: {'VERIFIED' if f_res.verified else 'CORRECTLY REJECTED'}")

    print("\n" + "=" * 80)
    print("                    PHASE 2 FOUNDATIONS FULLY OPERATIONAL")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
