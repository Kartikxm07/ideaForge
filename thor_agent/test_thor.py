"""
thor_agent.test_thor
────────────────────
10 Offline Self-Tests for Thor Sub-Agent:
Runs completely offline against the real pack and stub extractor.
Verifies all 10 core invariant requirements:
1. Bundle pack discovery (contracts, data, context, events)
2. Clause chunking with stable IDs (e.g. B1:5.2)
3. PyMuPDF twin PDF page matching and bounding box calculations
4. High-resolution PDF highlight PNG rendering
5. Verbatim quote verification (passes with verified status)
6. Quote repair (auto-heals misassigned chunk ID)
7. Fabricated quote rejection (hallucinated quote rejected, never stored)
8. Degraded regex fallback on timeout / offline mode
9. Non-LLM ingestion of context, ledger, and resilient malformed event skipping
10. SQLite odin_chunks + numpy vector matrix disk storage and cosine search
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List

from .ocr_pdf import PDFProcessor
from .storage import ChunkStorage
from .thor import ClauseChunk, ClauseChunker, ExtractedFact, OdinFeeder, ThorAgent, ThorExtractor

PACK_DIR = Path(__file__).resolve().parents[1] / "dataset" / "Pack" / "odin_dev_pack"


def run_all_tests():
    print("=" * 70)
    print(" THOR SUB-AGENT: RUNNING 10 OFFLINE SPECIFICATION CHECKS")
    print("=" * 70)

    results = []

    # Test 1: Pack Discovery
    try:
        feeder = OdinFeeder(str(PACK_DIR))
        files = feeder.discover_files()
        keys = [f["key"] for f in files]
        assert "contracts/B1.txt" in keys, "B1 contract must be discovered"
        assert "contracts/STD.txt" in keys, "STD contract must be discovered"
        assert "company/context.txt" in keys, "context.txt must be discovered"
        assert "data/payments_ledger.csv" in keys, "ledger must be discovered"
        assert "events/events_drop1.jsonl" in keys, "events must be discovered"
        results.append(("01. Bundle Pack Discovery", True, f"Discovered {len(files)} files"))
    except Exception as e:
        results.append(("01. Bundle Pack Discovery", False, str(e)))

    # Test 2: Clause Chunking & Stable IDs (B1:5.2)
    pdf_proc = PDFProcessor(pack_dir=str(PACK_DIR))
    chunker = ClauseChunker(pdf_proc)
    b1_path = PACK_DIR / "bundle" / "contracts" / "B1.txt"
    b1_pdf = PACK_DIR / "bundle" / "contracts" / "B1.pdf"
    with open(b1_path, "r", encoding="utf-8") as f:
        b1_text = f.read()

    try:
        chunks = chunker.chunk_contract(b1_text, "contracts/B1.txt", twin_pdf=b1_pdf)
        chunk_ids = [c.chunk_id for c in chunks]
        assert any("5.2" in cid for cid in chunk_ids), f"Expected stable ID with 5.2 in {chunk_ids}"
        assert any("3.1" in cid for cid in chunk_ids), f"Expected stable ID with 3.1 in {chunk_ids}"
        results.append(("02. Clause Chunking & Stable IDs", True, f"Generated {len(chunks)} chunks with stable IDs"))
    except Exception as e:
        results.append(("02. Clause Chunking & Stable IDs", False, str(e)))

    # Test 3: PyMuPDF Page Mapping & Bounding Box Rects
    try:
        quote = "Breach Notification Contents. The Data Breach notification must include"
        page_num, rects = pdf_proc.find_quote_page_and_rects(b1_pdf, quote, clause_ref="§5.2")
        assert page_num >= 2, f"Expected page >= 2 for B1:5.2, got {page_num}"
        assert len(rects) > 0, "Expected at least 1 bounding box rect for quote"
        assert len(rects[0]) == 4, "Rect must have [x0, y0, x1, y1] coordinates"
        results.append(("03. PyMuPDF Page & Rect Mapping", True, f"Mapped to page {page_num} with rect {rects[0]}"))
    except Exception as e:
        results.append(("03. PyMuPDF Page & Rect Mapping", False, str(e)))

    # Test 4: High-Res PDF Highlight PNG Rendering
    try:
        png_bytes, active_rects = pdf_proc.render_highlighted_page(b1_pdf, page_num=page_num, rects=rects)
        assert len(png_bytes) > 1000, f"PNG bytes too small: {len(png_bytes)}"
        assert png_bytes.startswith(b"\x89PNG"), "Output must be valid PNG binary format"
        results.append(("04. Highlighted PDF Page Rendering", True, f"Rendered {len(png_bytes)} bytes high-res PNG"))
    except Exception as e:
        results.append(("04. Highlighted PDF Page Rendering", False, str(e)))

    # Test 5: Verbatim Quote Verification (Valid quote passes)
    extractor = ThorExtractor()
    target_chunk = next(c for c in chunks if "5.2" in c.chunk_id)
    raw_fact = {
        "fact_type": "claim_windows",
        "chunk_id": target_chunk.chunk_id,
        "quote": "categories and approximate number of records affected",
        "value": "Breach notification detail requirement",
        "confidence": 0.95,
    }
    try:
        fact = extractor._verify_and_repair_quote(raw_fact, "contracts/B1.txt", chunks)
        assert fact is not None, "Valid quote must not be rejected"
        assert fact.status == "verified", f"Status should be verified, got {fact.status}"
        assert fact.chunk_id == target_chunk.chunk_id
        results.append(("05. Verbatim Quote Verification", True, "Valid quote successfully verified"))
    except Exception as e:
        results.append(("05. Verbatim Quote Verification", False, str(e)))

    # Test 6: Quote Repair (Auto-heals misassigned chunk ID)
    misassigned_fact = {
        "fact_type": "sla_tier",
        "chunk_id": "B1:wrong_chunk_99",  # Deliberately misassigned
        "quote": "Quillhub will make the Platform available at least ninety-nine and nine-tenths percent",
        "value": "99.9%",
        "confidence": 0.95,
    }
    try:
        repaired = extractor._verify_and_repair_quote(misassigned_fact, "contracts/B1.txt", chunks)
        assert repaired is not None, "Misassigned quote should be repaired, not rejected"
        assert repaired.status == "repaired", f"Status should be repaired, got {repaired.status}"
        assert "3.1" in repaired.chunk_id or "3" in repaired.chunk_id, f"Repaired chunk ID should be 3.1, got {repaired.chunk_id}"
        results.append(("06. Quote Chunk ID Auto-Repair", True, f"Repaired to {repaired.chunk_id}"))
    except Exception as e:
        results.append(("06. Quote Chunk ID Auto-Repair", False, str(e)))

    # Test 7: Fabricated Quote Rejection (Never stored)
    fake_fact = {
        "fact_type": "liability_caps",
        "chunk_id": target_chunk.chunk_id,
        "quote": "Quillhub warrants unlimited crypto-insurance indemnification of ten billion dollars.", # Hallucinated quote
        "value": "$10,000,000,000",
        "confidence": 0.99,
    }
    try:
        rejected = extractor._verify_and_repair_quote(fake_fact, "contracts/B1.txt", chunks)
        assert rejected is None, "Fabricated quote MUST be rejected and return None"
        results.append(("07. Fabricated Quote Rejection", True, "Hallucinated quote successfully rejected"))
    except Exception as e:
        results.append(("07. Fabricated Quote Rejection", False, str(e)))

    # Test 8: Degraded Regex Fallback
    try:
        fallback_facts = extractor._regex_fallback(b1_text, chunks)
        assert len(fallback_facts) > 0, "Fallback must extract clauses with patterns"
        assert any(f["fact_type"] == "sla_tier" for f in fallback_facts), "Fallback must detect 99.9% SLA tier"
        results.append(("08. Degraded Regex Fallback", True, f"Extracted {len(fallback_facts)} regex facts"))
    except Exception as e:
        results.append(("08. Degraded Regex Fallback", False, str(e)))

    # Test 9: Non-LLM Ingestion & Malformed Event Line Resilience
    tmp_dir = tempfile.mkdtemp()
    try:
        test_storage = ChunkStorage(
            db_path=os.path.join(tmp_dir, "test.db"),
            vector_path=os.path.join(tmp_dir, "test.npy")
        )
        test_agent = ThorAgent(pack_dir=str(PACK_DIR), storage=test_storage)

        # Ingest company context
        ctx_file = {"key": "company/context.txt", "abs_path": str(PACK_DIR / "bundle" / "company" / "context.txt"), "title": "Context", "source_type": "context_txt"}
        test_agent._ingest_non_contract(ctx_file)

        # Ingest ledger CSV
        csv_file = {"key": "data/payments_ledger.csv", "abs_path": str(PACK_DIR / "bundle" / "data" / "payments_ledger.csv"), "title": "Ledger", "source_type": "csv"}
        test_agent._ingest_non_contract(csv_file)

        # Create temporary malformed events file to test resilience
        bad_events_path = Path(tmp_dir) / "corrupt_events.jsonl"
        with open(bad_events_path, "w", encoding="utf-8") as f:
            f.write('{"id": "EV-01", "summary": "Valid Event 1"}\n')
            f.write('{THIS IS A CORRUPTED BROKEN LINE THAT SHOULD BE SKIPPED}\n')
            f.write('{"id": "EV-02", "summary": "Valid Event 2"}\n')

        bad_events_file = {"key": "events/corrupt_events.jsonl", "abs_path": str(bad_events_path), "title": "Corrupt Events", "source_type": "events_jsonl"}
        test_agent._ingest_non_contract(bad_events_file)

        all_c = test_storage.get_all_chunks()
        assert len(all_c) >= 3, f"Expected non-contract chunks in storage, got {len(all_c)}"
        results.append(("09. Non-LLM Ingest & Error Resilience", True, "Successfully ingested context/data and survived corrupt JSON lines"))
    except Exception as e:
        results.append(("09. Non-LLM Ingest & Error Resilience", False, str(e)))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Test 10: SQLite Storage, Vectors & Similarity Search
    tmp_dir2 = tempfile.mkdtemp()
    try:
        storage10 = ChunkStorage(
            db_path=os.path.join(tmp_dir2, "thor_store.db"),
            vector_path=os.path.join(tmp_dir2, "thor_store.npy")
        )
        pos = storage10.store_chunk(
            chunk_id="B1:5.2",
            document_id="contracts/B1.txt",
            text="The Data Breach notification must include description of nature of breach.",
            clause_ref="§5.2",
            page_num=3,
            char_start=1200,
            char_end=1350,
            rects=[[94.8, 76.1, 237.6, 86.7]]
        )
        assert pos["collection"] == "odin_chunks"
        assert pos["row_id"] == 1
        assert pos["page_num"] == 3
        assert pos["char_offsets"] == [1200, 1350]

        # Test vector search
        search_hits = storage10.search_similarity("unauthorized breach notification", top_k=1)
        assert len(search_hits) == 1, "Vector search should return hit"
        assert search_hits[0]["chunk_id"] == "B1:5.2"
        assert search_hits[0]["row_id"] == 1
        results.append(("10. SQLite odin_chunks & Vector Disk Search", True, f"Stored at row {pos['row_id']} and retrieved via vector search"))
    except Exception as e:
        results.append(("10. SQLite odin_chunks & Vector Disk Search", False, str(e)))
    finally:
        shutil.rmtree(tmp_dir2, ignore_errors=True)

    # Print summary
    print("\nTest Summary:")
    passed_all = True
    for name, ok, note in results:
        status_sym = "PASS" if ok else "FAIL"
        print(f"[{status_sym}] {name}: {note}")
        if not ok:
            passed_all = False

    print("=" * 70)
    if passed_all:
        print(" ALL 10 THOR OFFLINE SPECIFICATION CHECKS PASSED PERFECTLY!")
    else:
        print(" SOME CHECKS FAILED - PLEASE REVIEW")
    print("=" * 70)
    return passed_all


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
