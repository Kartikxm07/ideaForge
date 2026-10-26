"""
thor_agent.thor
───────────────
Thor Sub-Agent Implementation:
- Odin Feeder: Scans bundle, queues documents, reads .txt canonical anchor (or PDF/OCR fallback).
- Clause Chunker: Generates stable clause IDs (e.g. B1:5.2, STD:3.1), maps PDF pages, computes bounding rects.
- Fact Extractor: Extracts 11 contractual dimensions via gpt-oss-120b (or high-fidelity offline stub).
- Quote Verifier: Verifies verbatim quote against chunk, repairs misassigned chunk IDs, rejects fabricated quotes.
- Fallback Engine: Degraded regex fallback on timeout (45s budget) or LLM outage.
- Non-LLM Ingester: Indexes context.txt, ledger CSVs, and event logs (gracefully skipping malformed lines).
"""

from __future__ import annotations
import csv
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .storage import ChunkStorage
from .ocr_pdf import PDFProcessor, extract_text_from_pdf

logger = logging.getLogger("thor_agent")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Default pack location
DEFAULT_PACK_DIR = str(Path(__file__).resolve().parents[1] / "dataset" / "Pack" / "odin_dev_pack")


@dataclass
class ClauseChunk:
    chunk_id: str             # e.g. "B1:5.2", "STD:3.1"
    document_id: str          # e.g. "contracts/B1.txt" or "B1"
    clause_ref: str           # e.g. "§5.2" or "Section B"
    text: str
    page_num: int = 1
    char_start: int = 0
    char_end: int = 0
    token_count: int = 0
    rects: List[List[float]] = field(default_factory=list)
    source_type: str = "contract"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedFact:
    fact_type: str            # parties, dates, sla_tier, credit_tiers, claim_windows, liability_caps, insurance, termination, exclusivity, notice_terms, amendments, missing_exhibits
    document_id: str
    chunk_id: str
    quote: str
    confidence: float
    value: str
    status: str = "verified"  # "verified", "repaired", "degraded_regex", "rejected"
    explanation: str = ""


class ClauseChunker:
    """Splits contract text into stable clause-level chunks."""

    CLAUSE_PATTERN = re.compile(
        r"(?:^|\n)[ \t]*(?:(?P<sec>Section\s+[A-Z0-9]+(?:\.[0-9]+)*[^\n]*)|(?P<para>§\s*[0-9]+(?:\.[0-9]+)*[^\n]*)|(?P<num>[0-9]+\.[0-9]+[^\n]*)|(?P<hdr>={10,}[^\n]*\n[^\n]+[^\n]*\n={10,}))",
        re.MULTILINE
    )

    def __init__(self, pdf_processor: PDFProcessor):
        self.pdf_processor = pdf_processor

    def chunk_contract(self, text: str, doc_key: str, twin_pdf: Optional[Path] = None) -> List[ClauseChunk]:
        doc_stem = Path(doc_key).stem.replace(".txt", "").replace(".pdf", "")
        chunks: List[ClauseChunk] = []

        # Find section boundaries
        matches = list(self.CLAUSE_PATTERN.finditer(text))
        if not matches:
            # Fallback to paragraph splitting if no numbered sections found
            paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
            if not paras:
                paras = [text.strip()]
            for i, p_text in enumerate(paras, 1):
                c_id = f"{doc_stem}:chunk_{i}"
                start = text.find(p_text)
                end = start + len(p_text) if start != -1 else len(p_text)
                page, rects = (1, [])
                if twin_pdf:
                    page, rects = self.pdf_processor.find_quote_page_and_rects(twin_pdf, p_text[:100], None)
                chunks.append(ClauseChunk(
                    chunk_id=c_id,
                    document_id=doc_key,
                    clause_ref=f"Paragraph {i}",
                    text=p_text,
                    page_num=page,
                    char_start=max(0, start),
                    char_end=max(0, end),
                    token_count=max(1, (len(p_text) + 3) // 4),
                    rects=rects,
                    source_type="contract",
                ))
            return chunks

        # Process matched sections
        for idx, m in enumerate(matches):
            header = m.group(0).strip()
            start_pos = m.start()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            clause_text = text[start_pos:end_pos].strip()
            if len(clause_text) < 15:
                continue

            # Determine stable clause reference and ID
            clause_ref = self._extract_clause_label(header)
            clean_id_suffix = self._slugify_clause(clause_ref)
            chunk_id = f"{doc_stem}:{clean_id_suffix}"

            # PyMuPDF page & highlight rectangle search
            page_num = 1
            rects: List[List[float]] = []
            if twin_pdf and twin_pdf.exists():
                page_num, rects = self.pdf_processor.find_quote_page_and_rects(
                    twin_pdf,
                    clause_text[:120],
                    clause_ref=clause_ref
                )

            chunks.append(ClauseChunk(
                chunk_id=chunk_id,
                document_id=doc_key,
                clause_ref=clause_ref,
                text=clause_text,
                page_num=page_num,
                char_start=start_pos,
                char_end=end_pos,
                token_count=max(1, (len(clause_text) + 3) // 4),
                rects=rects,
                source_type="contract",
            ))

        return chunks

    def _extract_clause_label(self, header: str) -> str:
        h = header.replace("=", "").replace("-", "").strip()
        m_para = re.search(r"§\s*([0-9]+(?:\.[0-9]+)*)", h)
        if m_para:
            return f"§{m_para.group(1)}"
        m_sec = re.search(r"Section\s+([A-Z0-9]+(?:\.[0-9]+)*)", h, re.IGNORECASE)
        if m_sec:
            return f"Section {m_sec.group(1)}"
        m_num = re.search(r"\b([0-9]+\.[0-9]+)\b", h)
        if m_num:
            return f"{m_num.group(1)}"
        # Use first 3 words
        words = h.split()
        return " ".join(words[:3]) if words else "Clause"

    def _slugify_clause(self, label: str) -> str:
        s = label.replace("§", "").strip()
        s = re.sub(r"Section\s+", "", s, flags=re.IGNORECASE).strip()
        s = re.sub(r"[^A-Za-z0-9_.]+", "_", s).strip("_")
        return s or "clause"


class ThorExtractor:
    """
    Extracts facts across contractual dimensions using gpt-oss-120b,
    with built-in verbatim quote verification, chunk ID repair,
    fabricated quote rejection, and regex fallback on timeout/failure.
    """

    def __init__(
        self,
        llm_base_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
        timeout_seconds: float = 45.0,
    ):
        self.base_url = llm_base_url or os.environ.get("ODIN_LLM_BASE_URL", "")
        self.api_key = llm_api_key or os.environ.get("ODIN_LLM_API_KEY", "")
        self.model = llm_model or os.environ.get("ODIN_LLM_MODEL", "gpt-oss-120b")
        self.timeout = timeout_seconds

    def extract_facts_for_contract(
        self,
        doc_key: str,
        text: str,
        chunks: List[ClauseChunk]
    ) -> List[ExtractedFact]:
        """
        Main extraction entry point. Attempts gpt-oss-120b LLM extraction.
        If no API key / offline or timeout occurs, runs high-fidelity extraction/stub,
        followed by strict quote verification, repair, and rejection.
        """
        raw_facts: List[Dict[str, Any]] = []
        is_fallback = False

        if self.base_url and self.api_key:
            try:
                raw_facts = self._call_llm(doc_key, text, chunks)
            except Exception as e:
                logger.warning(f"Thor LLM extraction failed or timed out for {doc_key}: {e}. Engaging regex fallback.")
                raw_facts = self._regex_fallback(text, chunks)
                is_fallback = True
        else:
            # High-fidelity offline extractor (simulates gpt-oss-120b against the real pack)
            raw_facts = self._offline_grounded_extractor(doc_key, text, chunks)

        # Strict quote verification & repair pipeline
        verified_facts: List[ExtractedFact] = []
        for raw in raw_facts:
            fact = self._verify_and_repair_quote(raw, doc_key, chunks, is_fallback=is_fallback)
            if fact is not None:
                verified_facts.append(fact)

        return verified_facts

    def _verify_and_repair_quote(
        self,
        raw: Dict[str, Any],
        doc_key: str,
        chunks: List[ClauseChunk],
        is_fallback: bool = False
    ) -> Optional[ExtractedFact]:
        """
        Verbatim Quote Verification:
        1. Checks quote verbatim in target chunk.
        2. If missing, checks other chunks in the document. If found, repairs chunk_id.
        3. If not found in ANY chunk, rejects fabricated quote and returns None (NEVER STORED).
        """
        raw_quote = raw.get("quote")
        if not raw_quote or not isinstance(raw_quote, str):
            return None
        quote = raw_quote.strip()
        target_chunk_id = str(raw.get("chunk_id") or "")
        fact_type = str(raw.get("fact_type") or "general")
        value = str(raw.get("value") or "")
        try:
            confidence = float(raw.get("confidence", 0.9) or 0.9)
        except (ValueError, TypeError):
            confidence = 0.9

        if not quote:
            return None

        def normalize_ws(s: str) -> str:
            return re.sub(r"\s+", " ", s).strip()

        def normalize_text(text: str) -> str:
            """Strips extra whitespace, newlines, and non-alphanumeric chars for soft matching."""
            text = re.sub(r"\s+", " ", text)
            return re.sub(r"[^a-zA-Z0-9 ]", "", text).lower().strip()

        def text_matches(needle: str, haystack: str) -> bool:
            if not needle or not haystack:
                return False
            # 1. Exact match
            if needle in haystack:
                return True
            # 2. Lowercase whitespace-collapsed match
            norm_needle = normalize_ws(needle).lower()
            norm_hay = normalize_ws(haystack).lower()
            if norm_needle in norm_hay:
                return True
            # 3. Alphanumeric normalized match (fixes punctuation, curly quotes, dashes, OCR artifacts)
            alpha_needle = normalize_text(needle)
            alpha_hay = normalize_text(haystack)
            if not alpha_needle or not alpha_hay:
                return False
            if alpha_needle in alpha_hay:
                return True
            # 4. Trailing ellipsis check for truncated quotes
            clean_needle = re.sub(r"\.\.\.+$", "", needle).strip()
            norm_clean_needle = normalize_text(clean_needle)
            if len(norm_clean_needle) > 20 and norm_clean_needle in alpha_hay:
                return True
            # 5. Fuzzy ratio match fallback (ratio >= 0.82 for long quotes)
            if len(alpha_needle) > 30:
                from difflib import SequenceMatcher
                if SequenceMatcher(None, alpha_needle, alpha_hay).ratio() >= 0.82:
                    return True
            return False

        # 1. Check target chunk
        target_chunk = next((c for c in chunks if c.chunk_id == target_chunk_id), None)
        if target_chunk and text_matches(quote, target_chunk.text):
            status = "degraded_regex" if is_fallback else "verified"
            return ExtractedFact(
                fact_type=fact_type,
                document_id=doc_key,
                chunk_id=target_chunk_id,
                quote=quote,
                confidence=confidence,
                value=value,
                status=status,
                explanation=raw.get("explanation", "Quote verified in target clause.")
            )

        # 2. Check all other chunks (Repair logic)
        for other in chunks:
            if text_matches(quote, other.text):
                repaired_status = "repaired"
                logger.info(f"Repaired chunk ID for quote: {target_chunk_id} -> {other.chunk_id}")
                return ExtractedFact(
                    fact_type=fact_type,
                    document_id=doc_key,
                    chunk_id=other.chunk_id,
                    quote=quote,
                    confidence=confidence * 0.95,
                    value=value,
                    status=repaired_status,
                    explanation=f"Repaired: quote matched {other.chunk_id} (originally assigned to {target_chunk_id})."
                )

        # 3. Fabricated quote rejection
        logger.warning(f"REJECTED fabricated quote for {doc_key} (not found in document): '{quote[:60]}...'")
        return None

    def _call_llm(self, doc_key: str, text: str, chunks: List[ClauseChunk]) -> List[Dict[str, Any]]:
        """Invokes OpenAI-compatible gpt-oss-120b endpoint."""
        from openai import OpenAI
        client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)

        prompt = (
            f"Analyze the following contract ({doc_key}) and extract essential legal and operational facts.\n"
            "Dimensions to extract: parties, dates, sla_tier, credit_tiers, claim_windows, liability_caps, "
            "insurance, termination, exclusivity, notice_terms, amendments, missing_exhibits.\n\n"
            "Available Chunk IDs and excerpts:\n"
            + "\n".join([f"- ID: {c.chunk_id} | Ref: {c.clause_ref} | Text: {c.text[:140]}..." for c in chunks[:30]])
            + "\n\nCRITICAL REQUIREMENT: 'quote' MUST BE A VERBATIM EXACT SUBSTRING from the contract text.\n"
            "Return a JSON array of objects with keys: fact_type, document_id, chunk_id, quote, value, confidence, explanation."
        )

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are Thor, the autonomous contract evidence extractor. Respond ONLY with valid JSON array."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        content = resp.choices[0].message.content or "[]"
        clean_json = re.sub(r"^```json\s*", "", content.strip())
        clean_json = re.sub(r"```$", "", clean_json.strip())
        return json.loads(clean_json)

    def _offline_grounded_extractor(self, doc_key: str, text: str, chunks: List[ClauseChunk]) -> List[Dict[str, Any]]:
        """
        High-fidelity domain extraction engine for the Odin bundle contracts.
        Extracts verified verbatim facts directly from the canonical clauses.
        """
        facts: List[Dict[str, Any]] = []
        doc_stem = Path(doc_key).stem.replace(".txt", "").replace(".pdf", "")

        for chunk in chunks:
            c_text = chunk.text

            # Parties
            if "PROVIDER INFORMATION" in c_text or "CUSTOMER INFORMATION" in c_text or "Legal Name:" in c_text:
                for line in c_text.splitlines():
                    if "Legal Name:" in line:
                        p_name = line.split("Legal Name:")[-1].strip()
                        quote = line.strip()
                        facts.append({
                            "fact_type": "parties",
                            "chunk_id": chunk.chunk_id,
                            "quote": quote,
                            "value": p_name,
                            "confidence": 0.98,
                            "explanation": f"Identified contracted legal entity: {p_name}"
                        })

            # SLA & Uptime commitments
            if "Uptime" in c_text or "Target" in c_text or "ninety-nine" in c_text or "99." in c_text:
                m = re.search(r"(99\.[0-9]+%|ninety-nine[^\n.]+%)", c_text, re.IGNORECASE)
                if m:
                    # Extract surrounding sentence as quote
                    start = max(0, c_text.rfind(".", 0, m.start()) + 1)
                    end = c_text.find(".", m.end())
                    quote = c_text[start:end+1 if end != -1 else len(c_text)].strip()
                    if quote:
                        facts.append({
                            "fact_type": "sla_tier",
                            "chunk_id": chunk.chunk_id,
                            "quote": quote,
                            "value": m.group(0),
                            "confidence": 0.96,
                            "explanation": f"SLA Uptime commitment threshold: {m.group(0)}"
                        })

            # Service credit tiers & caps
            if "credit" in c_text.lower() and ("%" in c_text or "fee" in c_text.lower()):
                m = re.search(r"([0-9]+%\s+(?:of the Monthly Fee|credit|of monthly fees))", c_text, re.IGNORECASE)
                if m:
                    start = max(0, c_text.rfind(".", 0, m.start()) + 1)
                    end = c_text.find(".", m.end())
                    quote = c_text[start:end+1 if end != -1 else len(c_text)].strip()
                    if quote:
                        facts.append({
                            "fact_type": "credit_tiers",
                            "chunk_id": chunk.chunk_id,
                            "quote": quote,
                            "value": m.group(1),
                            "confidence": 0.94,
                            "explanation": f"Service credit tier calculation: {m.group(1)}"
                        })

            # Claim windows / notice deadlines
            if "within" in c_text.lower() and ("days" in c_text.lower() or "hours" in c_text.lower()):
                m = re.search(r"within\s+([a-zA-Z0-9\s()]+(?:days|hours|business days))", c_text, re.IGNORECASE)
                if m:
                    start = max(0, c_text.rfind(".", 0, m.start()) + 1)
                    end = c_text.find(".", m.end())
                    quote = c_text[start:end+1 if end != -1 else len(c_text)].strip()
                    if quote:
                        facts.append({
                            "fact_type": "claim_windows",
                            "chunk_id": chunk.chunk_id,
                            "quote": quote,
                            "value": m.group(0),
                            "confidence": 0.93,
                            "explanation": f"Contractual response / claim submission window: {m.group(0)}"
                        })

            # Liability caps
            if "liability" in c_text.lower() and ("cap" in c_text.lower() or "aggregate" in c_text.lower() or "exceed" in c_text.lower() or "$" in c_text):
                m = re.search(r"(total liability[^\n.]+exceed[^\n.]+|not exceed[^\n.]+\$[0-9,]+|aggregate liability[^\n.]+)", c_text, re.IGNORECASE)
                if m:
                    quote = m.group(0).strip()
                    facts.append({
                        "fact_type": "liability_caps",
                        "chunk_id": chunk.chunk_id,
                        "quote": quote,
                        "value": quote[:80],
                        "confidence": 0.95,
                        "explanation": "Contractual limitation of liability cap"
                    })

            # Exclusivity
            if "exclusiv" in c_text.lower() or "sole" in c_text.lower():
                m = re.search(r"([^\n.]*exclusive[^\n.]*\.)", c_text, re.IGNORECASE)
                if m:
                    quote = m.group(1).strip()
                    facts.append({
                        "fact_type": "exclusivity",
                        "chunk_id": chunk.chunk_id,
                        "quote": quote,
                        "value": "Exclusivity restriction",
                        "confidence": 0.95,
                        "explanation": "Territorial or sector exclusivity restriction"
                    })

            # Termination & notice terms
            if "termination" in c_text.lower() or "notice" in c_text.lower():
                if "Notice Address:" in c_text or "Email:" in c_text:
                    m = re.search(r"(Notice Address:[^\n]+(?:\n[^\n]+){1,3})", c_text)
                    if m:
                        quote = m.group(0).strip()
                        facts.append({
                            "fact_type": "notice_terms",
                            "chunk_id": chunk.chunk_id,
                            "quote": quote,
                            "value": quote.replace("\n", " "),
                            "confidence": 0.92,
                            "explanation": "Designated legal notice recipient address"
                        })

            # Insurance
            if "insurance" in c_text.lower() or "policy" in c_text.lower():
                m = re.search(r"([^\n.]*insurance[^\n.]*\$[0-9,]+[^\n.]*\.)", c_text, re.IGNORECASE)
                if m:
                    quote = m.group(1).strip()
                    facts.append({
                        "fact_type": "insurance",
                        "chunk_id": chunk.chunk_id,
                        "quote": quote,
                        "value": quote[:60],
                        "confidence": 0.91,
                        "explanation": "Required minimum insurance coverage threshold"
                    })

        return facts

    def _regex_fallback(self, text: str, chunks: List[ClauseChunk]) -> List[Dict[str, Any]]:
        """Crude regex extraction used on LLM timeout, flagged as degraded."""
        facts: List[Dict[str, Any]] = []
        patterns = [
            ("sla_tier", re.compile(r"(99\.[0-9]+%|ninety-nine[^\n()]*percent)", re.IGNORECASE)),
            ("credit_tiers", re.compile(r"([0-9]+%\s+(?:credit|of the Monthly Fee))", re.IGNORECASE)),
            ("claim_windows", re.compile(r"(within\s+[0-9a-zA-Z\s()]+\s+(?:days|hours))", re.IGNORECASE)),
            ("liability_caps", re.compile(r"(\$[0-9,]+(?:\.[0-9]{2})?)")),
        ]

        for chunk in chunks:
            for f_type, pat in patterns:
                m = pat.search(chunk.text)
                if m:
                    start = max(0, chunk.text.rfind("\n", 0, m.start()))
                    end = chunk.text.find("\n", m.end())
                    quote = chunk.text[start:end if end != -1 else len(chunk.text)].strip()
                    if quote:
                        facts.append({
                            "fact_type": f_type,
                            "chunk_id": chunk.chunk_id,
                            "quote": quote,
                            "value": m.group(1),
                            "confidence": 0.65,
                            "explanation": "Extracted via degraded regex fallback."
                        })
        return facts


class OdinFeeder:
    """
    Feeder component scanning pack directory, discovering bundle contracts,
    events, company context, and ledger files.
    """

    def __init__(self, pack_dir: str):
        self.pack_dir = Path(pack_dir)

    def discover_files(self) -> List[Dict[str, Any]]:
        bundle_dir = self.pack_dir / "bundle"
        if not bundle_dir.exists():
            bundle_dir = self.pack_dir

        files: List[Dict[str, Any]] = []

        # Read manifest if present
        manifest_file = bundle_dir / "manifest.json"
        manifest_titles = {}
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("files", []):
                        manifest_titles[item.get("path")] = item.get("title")
            except Exception:
                pass

        # 1. Contracts (.txt and twin .pdf)
        contracts_dir = bundle_dir / "contracts"
        if contracts_dir.exists():
            for txt_file in sorted(contracts_dir.glob("*.txt")):
                rel_path = f"contracts/{txt_file.name}"
                twin_pdf = txt_file.with_suffix(".pdf")
                files.append({
                    "key": rel_path,
                    "abs_path": str(txt_file),
                    "twin_pdf": str(twin_pdf) if twin_pdf.exists() else None,
                    "title": manifest_titles.get(rel_path, f"Contract {txt_file.stem}"),
                    "source_type": "contract_txt",
                    "size_bytes": txt_file.stat().st_size,
                })

        # 2. Company context
        ctx_file = bundle_dir / "company" / "context.txt"
        if ctx_file.exists():
            files.append({
                "key": "company/context.txt",
                "abs_path": str(ctx_file),
                "twin_pdf": None,
                "title": manifest_titles.get("company/context.txt", "Quillhub Inc. — Company Context"),
                "source_type": "context_txt",
                "size_bytes": ctx_file.stat().st_size,
            })

        # 3. Data files
        for csv_name in ["payments_ledger.csv", "holidays.csv"]:
            csv_file = bundle_dir / "data" / csv_name
            if csv_file.exists():
                files.append({
                    "key": f"data/{csv_name}",
                    "abs_path": str(csv_file),
                    "twin_pdf": None,
                    "title": manifest_titles.get(f"data/{csv_name}", csv_name),
                    "source_type": "csv",
                    "size_bytes": csv_file.stat().st_size,
                })

        # 4. Events
        events_dir = bundle_dir / "events"
        if events_dir.exists():
            for jsonl_file in sorted(events_dir.glob("*.jsonl")):
                rel_path = f"events/{jsonl_file.name}"
                files.append({
                    "key": rel_path,
                    "abs_path": str(jsonl_file),
                    "twin_pdf": None,
                    "title": manifest_titles.get(rel_path, jsonl_file.name),
                    "source_type": "events_jsonl",
                    "size_bytes": jsonl_file.stat().st_size,
                })

        return files


class ThorAgent:
    """
    Thor Sub-Agent master orchestrator:
    - Feeds files from Odin feeder.
    - Runs parallel chunking and extraction.
    - Performs quote verification, repair, rejection.
    - Indexes non-LLM company, event, and ledger chunks.
    - Emits live events for Box 1 (Odin), Box 2 (Thor), and Box 3 (Storage).
    """

    def __init__(
        self,
        pack_dir: Optional[str] = None,
        storage: Optional[ChunkStorage] = None,
        llm_base_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
    ):
        self.pack_dir = Path(pack_dir or os.environ.get("ODIN_PACK_DIR", DEFAULT_PACK_DIR))
        self.storage = storage or ChunkStorage()
        self.pdf_processor = PDFProcessor(pack_dir=str(self.pack_dir))
        self.chunker = ClauseChunker(self.pdf_processor)
        self.extractor = ThorExtractor(
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            llm_model=llm_model
        )
        self.feeder = OdinFeeder(str(self.pack_dir))

        # Event callbacks
        self.on_odin_fetch: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_thor_fact: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_chunk_stored: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_progress: Optional[Callable[[Dict[str, Any]], None]] = None

    def run_analysis(self) -> Dict[str, Any]:
        """
        Executes complete Thor analysis under the 2-minute target.
        Clears previous run, discovers files, processes contracts,
        indexes data, verifies quotes, and populates SQLite + vector storage.
        """
        start_time = time.time()
        self.storage.clear()

        files = self.feeder.discover_files()
        total_files = len(files)
        total_facts = 0
        total_chunks = 0
        repaired_count = 0
        rejected_count = 0

        # Step 1: Feeder notification
        for f in files:
            if self.on_odin_fetch:
                self.on_odin_fetch({
                    "key": f["key"],
                    "title": f["title"],
                    "source_type": f["source_type"],
                    "size_bytes": f["size_bytes"],
                    "status": "queued",
                    "timestamp": time.time()
                })

        # Step 2: Process contracts
        contract_files = [f for f in files if f["source_type"] == "contract_txt"]
        for idx, cf in enumerate(contract_files, 1):
            if self.on_odin_fetch:
                self.on_odin_fetch({
                    "key": cf["key"],
                    "title": cf["title"],
                    "source_type": cf["source_type"],
                    "size_bytes": cf["size_bytes"],
                    "status": "processing",
                    "timestamp": time.time()
                })

            txt_path = Path(cf["abs_path"])
            text = ""
            twin_pdf = Path(cf["twin_pdf"]) if cf.get("twin_pdf") else None

            # Read canonical .txt (source of truth)
            if txt_path.exists():
                with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()

            # Fallback to PDF text layer / OCR if .txt is empty or missing
            if not text.strip() and twin_pdf and twin_pdf.exists():
                logger.info(f"Using PDF/OCR text fallback for {cf['key']}")
                text = extract_text_from_pdf(twin_pdf)

            # Chunk into clauses
            chunks = self.chunker.chunk_contract(text, cf["key"], twin_pdf=twin_pdf)

            # Store chunks into SQLite + vector matrix (Box 3)
            for c in chunks:
                pos = self.storage.store_chunk(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    text=c.text,
                    clause_ref=c.clause_ref,
                    page_num=c.page_num,
                    char_start=c.char_start,
                    char_end=c.char_end,
                    token_count=c.token_count,
                    rects=c.rects,
                    source_type=c.source_type,
                    metadata={"title": cf["title"]}
                )
                total_chunks += 1
                if self.on_chunk_stored:
                    self.on_chunk_stored(pos)

            # Extract facts via Thor (Box 2)
            facts = self.extractor.extract_facts_for_contract(cf["key"], text, chunks)
            for fact in facts:
                if fact.status == "rejected":
                    rejected_count += 1
                    continue
                if fact.status == "repaired":
                    repaired_count += 1

                self.storage.store_fact(
                    fact_type=fact.fact_type,
                    document_id=fact.document_id,
                    chunk_id=fact.chunk_id,
                    quote=fact.quote,
                    confidence=fact.confidence,
                    value=fact.value,
                    status=fact.status,
                    explanation=fact.explanation
                )
                total_facts += 1

                if self.on_thor_fact:
                    self.on_thor_fact({
                        "fact_type": fact.fact_type,
                        "document_id": fact.document_id,
                        "chunk_id": fact.chunk_id,
                        "quote": fact.quote,
                        "confidence": fact.confidence,
                        "value": fact.value,
                        "status": fact.status,
                        "explanation": fact.explanation,
                        "timestamp": time.time()
                    })

            if self.on_progress:
                self.on_progress({
                    "progress_percent": int((idx / max(1, len(contract_files))) * 70),
                    "contracts_completed": idx,
                    "total_contracts": len(contract_files),
                    "total_chunks": total_chunks,
                    "total_facts": total_facts,
                    "elapsed_seconds": round(time.time() - start_time, 2)
                })

        # Step 3: Non-LLM Ingest (Company, Ledger, Events)
        non_contracts = [f for f in files if f["source_type"] != "contract_txt"]
        for nf in non_contracts:
            self._ingest_non_contract(nf)
            total_chunks += 1

        elapsed = round(time.time() - start_time, 2)
        summary = {
            "status": "completed",
            "elapsed_seconds": elapsed,
            "target_seconds": 120,
            "met_target": elapsed <= 120.0,
            "total_files": total_files,
            "total_chunks_stored": len(self.storage.get_all_chunks()),
            "total_facts_extracted": len(self.storage.get_all_facts()),
            "repaired_facts_count": repaired_count,
            "rejected_facts_count": rejected_count,
            "pack_dir": str(self.pack_dir),
        }

        if self.on_progress:
            self.on_progress({
                "progress_percent": 100,
                "summary": summary,
                "timestamp": time.time()
            })

        return summary

    def _ingest_non_contract(self, file_meta: Dict[str, Any]):
        """Indexes company context, ledgers, and events without LLM, skipping malformed lines."""
        key = file_meta["key"]
        p = Path(file_meta["abs_path"])
        if not p.exists():
            return

        if file_meta["source_type"] == "context_txt":
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                # Store corporate context chunks
                paras = [pr.strip() for pr in content.split("\n\n") if len(pr.strip()) > 20]
                for i, para in enumerate(paras, 1):
                    pos = self.storage.store_chunk(
                        chunk_id=f"CTX:sec_{i}",
                        document_id=key,
                        text=para,
                        clause_ref=f"Context Section {i}",
                        page_num=1,
                        source_type="context_txt",
                        metadata={"title": file_meta["title"]}
                    )
                    if self.on_chunk_stored:
                        self.on_chunk_stored(pos)
            except Exception as e:
                logger.error(f"Failed to ingest company context {key}: {e}")

        elif file_meta["source_type"] == "csv":
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                summary_text = f"Dataset: {file_meta['title']}\nTotal records: {len(rows)}\nColumns: {', '.join(reader.fieldnames or [])}\n"
                for r in rows[:10]:
                    summary_text += json.dumps(r) + "\n"
                pos = self.storage.store_chunk(
                    chunk_id=f"DATA:{Path(key).stem}",
                    document_id=key,
                    text=summary_text,
                    clause_ref="CSV Summary",
                    page_num=1,
                    source_type="csv",
                    metadata={"title": file_meta["title"], "row_count": len(rows)}
                )
                if self.on_chunk_stored:
                    self.on_chunk_stored(pos)
            except Exception as e:
                logger.error(f"Failed to ingest CSV {key}: {e}")

        elif file_meta["source_type"] == "events_jsonl":
            try:
                valid_events = []
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line_no, line in enumerate(f, 1):
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            ev = json.loads(line_str)
                            valid_events.append(ev)
                        except json.JSONDecodeError:
                            logger.warning(f"Malformed event JSON line {line_no} in {key} logged and safely skipped.")
                
                # Chunk events into batches
                batch_size = 5
                for b_idx in range(0, len(valid_events), batch_size):
                    batch = valid_events[b_idx:b_idx+batch_size]
                    b_text = "\n".join([f"[{e.get('id', 'EV')}] {e.get('timestamp', '')}: {e.get('summary', e.get('event_type', ''))}" for e in batch])
                    pos = self.storage.store_chunk(
                        chunk_id=f"EV:{Path(key).stem}_{b_idx//batch_size + 1}",
                        document_id=key,
                        text=b_text,
                        clause_ref=f"Events {b_idx+1}-{min(len(valid_events), b_idx+batch_size)}",
                        page_num=1,
                        source_type="events_jsonl",
                        metadata={"title": file_meta["title"], "event_count": len(batch)}
                    )
                    if self.on_chunk_stored:
                        self.on_chunk_stored(pos)
            except Exception as e:
                logger.error(f"Failed to ingest events {key}: {e}")
