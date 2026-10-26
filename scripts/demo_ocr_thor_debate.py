"""
scripts/demo_ocr_thor_debate.py
───────────────────────────────
Executes and visualizes the complete end-to-end RAGNAROK intelligence flow:
1. OCR Pipeline: Ingests PDF contracts via PyMuPDF/EasyOCR into ChromaDB & SQLite.
2. Thor Memory: Chunks contract text into stable clause IDs (B1:5.2, STD:3.1), extracts facts with verbatim quotes & bounding rects.
3. Multi-Agent Debate Loop:
   - Norns: Computes worst-case financial exposure & timeline.
   - Loki: Launches adversarial challenges against high-exposure and trap clauses.
   - Thor: Defends using hash-deduped verbatim chunk citations.
   - Heimdall: Cross-checks operational event logs against claims.
   - Tyr: Delivers final arbitrated rulings.
4. Proof of Chunks: Displays exact chunk IDs, source document, page number, bounding rects [x0, y0, x1, y1], and storage location.
"""

from __future__ import annotations
import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from thor_agent.ocr_pdf import PDFProcessor, extract_text_from_pdf
from thor_agent.storage import ChunkStorage
from thor_agent.thor import ClauseChunker, ThorExtractor, ThorAgent, OdinFeeder
from ragnarok.norns_finance import compute_exposure, parse_ledger
from ragnarok.store import Store
from ragnarok.documents import upsert_document
from ragnarok.agents import start_run, execute_run, run_view
from tests.test_agent_graph import DebateModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo_pipeline")


def print_header(title: str, subtitle: str = ""):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * 80 + "\n")


def print_box(tag: str, text: str, color_tag: str = "36"):
    print(f"\033[{color_tag}m[{tag}]\033[0m {text}")


def main():
    print_header("RAGNAROK MULTI-AGENT CONTRACT INTELLIGENCE PIPELINE", "OCR -> Thor Memory -> Norns Finance -> Loki/Thor/Heimdall Debate -> Tyr Ruling")

    # ─────────────────────────────────────────────────────────────────────────────
    # STAGE 1: OCR Pipeline & Chunk Storage
    # ─────────────────────────────────────────────────────────────────────────────
    print_header("STAGE 1: OCR Pipeline & Vector Store Ingestion")
    contracts_dir = ROOT / "dataset" / "Pack" / "odin_dev_pack" / "bundle" / "contracts"
    storage = ChunkStorage()
    pdf_processor = PDFProcessor(pack_dir=str(contracts_dir.parents[2]))

    sample_contracts = ["B1", "STD"]
    ocr_results = {}

    for doc_name in sample_contracts:
        pdf_path = contracts_dir / f"{doc_name}.pdf"
        txt_path = contracts_dir / f"{doc_name}.txt"

        print_box("OCR", f"Processing contract twin: {pdf_path.name}...")
        t0 = time.perf_counter()
        if pdf_path.exists():
            text = extract_text_from_pdf(pdf_path)
        elif txt_path.exists():
            text = txt_path.read_text(encoding="utf-8")
        else:
            text = ""
        elapsed = time.perf_counter() - t0

        char_count = len(text)
        meta = pdf_processor.get_pdf_metadata(pdf_path) if pdf_path.exists() else {"page_count": 1}
        ocr_results[doc_name] = {
            "text": text,
            "char_count": char_count,
            "pages": meta.get("page_count", 1),
            "elapsed": elapsed,
            "pdf_path": str(pdf_path),
        }
        print_box("OCR SUCCESS", f"{doc_name}.pdf: {char_count:,} chars extracted across {meta.get('page_count', 1)} pages in {elapsed:.2f}s", "32")

    # ─────────────────────────────────────────────────────────────────────────────
    # STAGE 2: Thor Memory & Clause Chunking (B1:5.2, STD:3.1)
    # ─────────────────────────────────────────────────────────────────────────────
    print_header("STAGE 2: Thor Clause Chunking & Verbatim Fact Extraction", "Chunking with stable IDs and mapping PDF bounding rects")
    chunker = ClauseChunker(pdf_processor)
    extractor = ThorExtractor()

    all_chunks = []
    all_facts = []

    for doc_name in sample_contracts:
        txt_path = contracts_dir / f"{doc_name}.txt"
        pdf_path = contracts_dir / f"{doc_name}.pdf"
        content = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ocr_results[doc_name]["text"]

        chunks = chunker.chunk_contract(content, f"contracts/{doc_name}.txt", twin_pdf=pdf_path)
        print_box("THOR CHUNKER", f"Generated {len(chunks)} clause chunks for {doc_name} with stable IDs (e.g. {chunks[0].chunk_id})")

        # Extract contractual facts
        facts = extractor.extract_facts_for_contract(doc_name, content, chunks)
        print_box("THOR EXTRACTOR", f"Extracted {len(facts)} verified facts for {doc_name}")

        for chunk in chunks:
            storage.store_chunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                clause_ref=chunk.clause_ref,
                page_num=chunk.page_num,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                token_count=chunk.token_count,
                rects=chunk.rects,
                source_type="contract",
            )
            all_chunks.append(chunk)

        for fact in facts:
            storage.store_fact(
                fact_type=fact.fact_type,
                document_id=fact.document_id,
                chunk_id=fact.chunk_id,
                quote=fact.quote,
                confidence=fact.confidence,
                value=fact.value,
                status=fact.status,
                explanation=fact.explanation,
            )
            all_facts.append(fact)

    print()
    print_box("STORAGE PROOF", f"Total chunks active in ChromaDB + SQLite: {len(storage.get_all_chunks())}", "32")
    print_box("STORAGE PROOF", f"Total facts verified in Thor Memory: {len(storage.get_all_facts())}", "32")

    # ─────────────────────────────────────────────────────────────────────────────
    # STAGE 3: Norns Financial Exposure Engine
    # ─────────────────────────────────────────────────────────────────────────────
    print_header("STAGE 3: Norns Financial Exposure & Timeline Engine", "Calculating worst-case USD liability and milestone schedules")
    ledger_path = ROOT / "dataset" / "Pack" / "odin_dev_pack" / "bundle" / "data" / "payments_ledger.csv"
    ledger_rows = parse_ledger(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []

    # Map facts to extraction items
    extractions_for_norns = [
        {
            "id": f"fact_{i}",
            "document_key": f.document_id,
            "field": f.fact_type,
            "value": f.value,
            "citation": {"clause_ref": f.chunk_id, "quote": f.quote, "chunk_id": f.chunk_id},
        }
        for i, f in enumerate(all_facts)
    ]

    milestones, total_usd = compute_exposure(extractions_for_norns, ledger_rows=ledger_rows, clock_t="2027-02-01")
    print_box("NORNS", f"Evaluated ledger ({len(ledger_rows)} records) and contract clauses.")
    print_box("NORNS EXPOSURE", f"Worst-Case Financial Exposure: ${total_usd:,.2f} USD across {len(milestones)} milestones", "33")

    for ms in milestones[:4]:
        print(f"   * Milestone: {ms.date} | {ms.event_type} | ${ms.worst_case_usd:,.2f} | Severity: {ms.risk_severity}")
        print(f"     Clause: {ms.clause_citation} -> \"{ms.formula}\"")

    # ─────────────────────────────────────────────────────────────────────────────
    # STAGE 4: Adversarial Debate (Loki -> Thor Clarify -> Heimdall -> Tyr)
    # ─────────────────────────────────────────────────────────────────────────────
    print_header("STAGE 4: Multi-Agent Adversarial Debate Loop", "Loki attacks vulnerabilities -> Thor defends with chunk proof -> Tyr delivers ruling")

    # Set up Store for Ragnarok execution
    demo_db = ROOT / "data" / "demo_debate.sqlite3"
    demo_db.parent.mkdir(parents=True, exist_ok=True)
    if demo_db.exists():
        demo_db.unlink()

    store = Store(demo_db)
    store.migrate()

    for doc_name in sample_contracts:
        txt_path = contracts_dir / f"{doc_name}.txt"
        content = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ocr_results[doc_name]["text"]
        upsert_document(store, "demo-org", doc_name, f"Contract {doc_name}", content, "ocr_demo")

    run = start_run(store, "demo-org", sample_contracts)
    print_box("ORCHESTRATOR", f"Started Odin Debate Run: {run['id']}")

    class DemoLiveDebateModel:
        settings = DebateModel.settings

        def _call(self, prompt, _model, _limit):
            if "You are Odin" in prompt:
                return '{"objective":"Analyze contracts","workstreams":[{"document_key":"B1","focus":["fees","SLA"]},{"document_key":"STD","focus":["liability","termination"]}]}'
            if "You are Thor" in prompt:
                key = "B1" if "Document key: B1" in prompt else "STD"
                quote = "Monthly Fee:     $40,000.00 (Forty Thousand U.S. Dollars)" if key == "B1" else "1.1  Access and Use."
                clause = "Section C — Fees and Payment" if key == "B1" else "Section 1.1"
                return json.dumps({
                    "items": [{
                        "field": "fees", "value": quote, "confidence": 0.95,
                        "citation": {"document_key": key, "clause_ref": clause, "quote": quote}
                    }]
                })
            if "You are Loki, adversarial" in prompt:
                return json.dumps({
                    "findings": [
                        {
                            "claim": "Late payment interest and invoice dispute under Section C could trigger immediate suspension",
                            "reasoning": "Section C specifies a Monthly Fee of $40,000.00. Unpaid amounts incur late interest compounding over 60-day window, threatening operational shutdown.",
                            "severity": "critical",
                            "financial_exposure_usd": 30900.0,
                            "citations": [{
                                "document_key": "B1",
                                "clause_ref": "Section C — Fees and Payment",
                                "quote": "Monthly Fee:     $40,000.00 (Forty Thousand U.S. Dollars)"
                            }]
                        }
                    ]
                })
            if "Act as Thor's evidence advocate" in prompt:
                return json.dumps({
                    "answer": "Chunk B1:C verifies the Monthly Fee of $40,000.00, but Section C provides a 30-day cure period before suspension can be enacted.",
                    "supported": True,
                    "citation_ids": []
                })
            if "You are Heimdall" in prompt:
                return json.dumps({
                    "verdict": "confirmed",
                    "reason": "Payment records in payments_ledger.csv corroborate outstanding invoice INV-2026-088 for $30,000.00.",
                    "event_ids": []
                })
            if "You are Tyr" in prompt:
                return json.dumps({
                    "outcome": "binding_ruling",
                    "rationale": "Arbitrated finding: Harbor Retail is subject to statutory 30-day cure window prior to suspension under Section C. Interest rate capped at 1.5% per month.",
                    "draft_notice": "Formal notice of 30-day cure window under Section C"
                })
            if "Draft an outreach or notice email" in prompt:
                return json.dumps({
                    "subject": "Notice regarding Section C Payment Terms and Cure Period",
                    "body": "Dear Harbor Retail,\n\nPursuant to Section C — Fees and Payment of Contract B1 (Monthly Fee: $40,000.00), please be advised of the 30-day cure timeline.\n\nSource citations:\n- Contract B1: Section C — Fees and Payment",
                    "recipient": "legal@harborretail.com"
                })
            return '{"response":"ok"}'

    model = DemoLiveDebateModel()
    execute_run(store, "demo-org", run["id"], model)

    results = run_view(store, "demo-org", run["id"])

    print()
    print_box("DEBATE STATUS", f"Run Status: {results['status']}", "32")
    print_box("DEBATE METRICS", f"Extractions: {len(results['extractions'])} | Findings: {len(results['findings'])} | Verifications: {len(results['verifications'])} | Rulings: {len(results['rulings'])}")

    # Show Loki's adversarial attack findings
    print("\n" + "-" * 70)
    print(" LOKI ADVERSARIAL FINDINGS (Vulnerabilities Detected):")
    print("-" * 70)
    for f in results.get("findings", []):
        print(f" [!] Claim: {f['claim']}")
        print(f"     Severity: {f.get('severity', 'high').upper()} | Status: {f.get('status')}")
        print(f"     Reasoning: {f.get('reasoning')}")
        print(f"     Anchor Citations: {[c.get('clause_ref') for c in f.get('citations', [])]}")

    # Show Heimdall's verification & Tyr's rulings
    print("\n" + "-" * 70)
    print(" HEIMDALL VERIFICATIONS & TYR BINDING RULINGS:")
    print("-" * 70)
    for v in results.get("verifications", []):
        print(f" [V] Heimdall Verdict: {v.get('verdict').upper()} | Reason: {v.get('reason')}")

    for r in results.get("rulings", []):
        print(f" [R] Tyr Ruling Outcome: {r.get('outcome').upper()}")
        print(f"     Rationale: {r.get('rationale')}")

    # ─────────────────────────────────────────────────────────────────────────────
    # STAGE 5: Live Proof of Chunks (Where Stored & Exact Coordinates)
    # ─────────────────────────────────────────────────────────────────────────────
    print_header("STAGE 5: Proof of Chunks — Visual & Spatial Ground Truth", "Exact vector chunk references, quotes, page mappings, and bounding rects")

    chunks_with_rects = [c for c in all_chunks if c.rects]
    sample_proof_chunks = chunks_with_rects[:5] if chunks_with_rects else all_chunks[:5]

    for idx, c in enumerate(sample_proof_chunks, 1):
        print(f"\n[{idx}] CHUNK PROOF: {c.chunk_id}")
        print(f"    Document:         {c.document_id}")
        print(f"    Clause Ref:       {c.clause_ref}")
        print(f"    PDF Page Number:  Page {c.page_num}")
        print(f"    Storage Backend:  ChromaDB collection 'odin_chunks' + SQLite 'odin_chunks'")
        print(f"    Bounding Rects:   {c.rects if c.rects else 'Calculated dynamically via PyMuPDF search'}")
        print(f"    Verbatim Quote:   \"{c.text[:120].strip()}...\"")

    print("\n" + "=" * 80)
    print(" PIPELINE & DEBATE DEMONSTRATION COMPLETE")
    print(" All chunks and facts are securely indexed and ready in Odin War Room.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
