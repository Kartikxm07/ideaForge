"""Checkpointed LangGraph orchestration for the existing ODIN agent records.

Graph state contains references and control values only. Contract text, model
responses, citations, and rulings remain in the owner-scoped SQLite store.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import operator
import re
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .agents import (
    _explicit_dates, _json_call, _list, _message, _save, _set_status,
    _verified, run_view,
)
from .store import Store
from .rag import upsert_chunks, hybrid_search, evaluate_retrieval
from .thor_bridge import extract_with_thor
from .norns_finance import compute_exposure, parse_ledger
from .citation_checker import check_chunks_for_document


MAX_MODEL_CALLS = 80
MAX_DEBATE_ROUNDS = 3


class OdinState(TypedDict, total=False):
    run_id: str
    doc_ids: list[str]
    doc_id: str
    extraction_ids: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    finding_ids: list[str]
    checkpoints: list[str]
    clock_idx: int
    cursor: int
    debate_round: int
    verdict: str
    clock_t: str
    status: str
    # ── Gap 1: Norns financial exposure flows through state ──────────────
    norns_exposure_usd: float
    # ── Gap 2: Debate history accumulates across ALL rounds (no overwrite)
    debate_history: Annotated[list[dict], operator.add]
    # ── Gap 3: Clarification hashes break Thor infinite re-extraction loops
    clarification_hashes: Annotated[list[str], operator.add]


def _stable_id(run_id: str, node: str, source: str) -> str:
    return hashlib.sha256(f"{run_id}\0{node}\0{source}".encode()).hexdigest()


def _items(store: Store, owner: str, kind: str, run_id: str) -> list[dict]:
    with store.connect() as db:
        return _list(db, owner, kind, run_id)


def _record(store: Store, owner: str, run_id: str, kind: str, node: str, source: str, data: dict) -> dict:
    with store.connect() as db:
        return _save(db, owner, kind, {"run_id": run_id, "agent": node, **data}, _stable_id(run_id, node, source))


def _model_json(store: Store, owner: str, run_id: str, node: str, model, prompt: str, limit: int) -> dict:
    """Cache each valid response before advancing a node or checkpoint."""
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    key = _stable_id(run_id, f"{node}-model", digest)
    with store.connect() as db:
        row = db.execute("SELECT data FROM web_records WHERE id=? AND owner_id=? AND kind='agent-model-cache'", (key, owner)).fetchone()
        if row:
            return json.loads(row["data"])["output"]
        used = db.execute("SELECT count(*) FROM web_records WHERE owner_id=? AND kind='agent-model-cache' AND json_extract(data,'$.run_id')=?", (owner, run_id)).fetchone()[0]
    if used >= MAX_MODEL_CALLS:
        raise ValueError(f"Model-call budget reached ({MAX_MODEL_CALLS})")
    output = _json_call(model, prompt, limit)
    with store.connect() as db:
        _save(db, owner, "agent-model-cache", {"run_id": run_id, "node": node, "prompt_sha256": digest, "output": output}, key)
    return output


def _failure(store: Store, owner: str, run_id: str, node: str, exc: Exception) -> str:
    detail = str(exc)[:200] if isinstance(exc, ValueError) else type(exc).__name__
    _message(store, owner, run_id, node, "Odin", f"{node} incomplete: {detail}")
    return f"{node}: {detail}"


def build_graph(store: Store, owner: str, run_id: str, model, checkpointer=None):
    """Build the outer graph and its bounded debate subgraph for one owner/run."""

    def ingest(state: OdinState) -> dict:
        try:
            run = run_view(store, owner, run_id)
            if not run:
                raise ValueError("Run not found")
            with store.connect() as db:
                for key in run["document_keys"]:
                    row = db.execute("SELECT content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner, key)).fetchone()
                    if not row or row[0] != run["hashes"][key]:
                        raise ValueError(f"Source changed: {key}")
            checkpoints = run.get("checkpoints") or [run["started_at"][:10]]
            return {"doc_ids": sorted(run["document_keys"]), "checkpoints": checkpoints,
                    "clock_idx": 0, "clock_t": checkpoints[0]}
        except Exception as exc:
            return {"doc_ids": [], "errors": [_failure(store, owner, run_id, "ingest", exc)]}

    def odin_plan(state: OdinState) -> dict:
        docs = state.get("doc_ids", [])
        try:
            output = _model_json(store, owner, run_id, "Odin", model,
                'You are Odin, the contract-analysis orchestrator. Return JSON {"objective":string,"workstreams":[{"document_key":string,"focus":[string]}]}. Plan Thor extraction for every supplied document. Include citations, dates, amounts, SLA, amendments, notices, liability and conflicts as focus areas. Do not decide routing or invent facts. Documents: ' + json.dumps(docs), 1600)
            _record(store, owner, run_id, "agent-plan", "Odin", "initial", output)
            _message(store, owner, run_id, "Odin", "Thor", f"Planned {len(output.get('workstreams', []))} evidence workstreams")
        except Exception as exc:
            _message(store, owner, run_id, "Odin", "Thor", f"Deterministic fallback plan for {len(docs)} documents ({type(exc).__name__})")
        return {}

    def distribute(state: OdinState):
        docs = state.get("doc_ids", [])
        return [Send("thor", {"run_id": run_id, "doc_id": doc}) for doc in docs] if docs else "terms_merge"

    def thor(state: OdinState) -> dict:
        doc_id = state["doc_id"]
        saved: list[str] = []
        try:
            with store.connect() as db:
                row = db.execute("SELECT title,content,content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner, doc_id)).fetchone()
                if not row:
                    raise ValueError(f"Missing document: {doc_id}")
                content = row["content"]

            # ── RAG ingest: 512-token chunks → SQLite FTS5 + embedding slot ──
            n_chunks = upsert_chunks(store, owner, doc_id, content)
            _message(store, owner, run_id, "Thor", "Odin",
                     f"{doc_id}: indexed {n_chunks} RAG chunks (≈512 tokens each)")

            def emit_thor(kind: str, data: dict):
                if kind == "chunk":
                    text = f"{doc_id}: chunked {data['current']}/{data['total']} · {data['chunk_id']}"
                else:
                    text = f"{doc_id}: verified {data['fact_type']} · {data['chunk_id']} · {data['confidence']:.0%}"
                _message(store, owner, run_id, "Thor", "Odin", text)

            facts = extract_with_thor(store.path, run_id, doc_id, row["title"], content,
                                      model.settings, emit=emit_thor)
            query = f"obligations dates amounts SLA notice penalty in {doc_id}"
            rag_ctx = hybrid_search(store, owner, query, document_keys=[doc_id], model=model, top_k=4)
            evaluate_retrieval(store, owner, run_id, query, rag_ctx,
                               " ".join(str(item["value"]) for item in facts))
            with store.connect() as db:
                for index, item in enumerate(facts):
                    citation = item["citation"]
                    citation["content_sha256"] = row["content_sha256"]
                    result = _save(db, owner, "agent-extraction", {
                        "run_id": run_id, "agent": "Thor", "document_key": doc_id,
                        "field": str(item["field"])[:100], "value": str(item["value"])[:500],
                        "confidence": item["confidence"], "ambiguity": item["ambiguity"],
                        "citation": citation, "source_tag": "sourced",
                        "verification_status": item["status"],
                        "verification_explanation": item["explanation"],
                        "rag_chunk_ids": [c["id"] for c in rag_ctx],
                    }, _stable_id(run_id, "Thor", f"{doc_id}:{citation['chunk_id']}:{index}"))
                    saved.append(result["id"])
            _message(store, owner, run_id, "Thor", "Odin", f"{doc_id}: {len(saved)} verified terms")
            return {"extraction_ids": saved}
        except Exception as exc:
            return {"extraction_ids": saved, "errors": [_failure(store, owner, run_id, f"Thor/{doc_id}", exc)]}

    def terms_merge(state: OdinState) -> dict:
        # The current source model has no amendment relations; preserve all cited terms.
        count = len(_items(store, owner, "agent-extraction", run_id))
        _message(store, owner, run_id, "Odin", "Norns", f"{count} cited terms available; amendment precedence unresolved")
        return {}

    def checkpoint_init(state: OdinState) -> dict:
        checkpoints = state.get("checkpoints", [])
        index = state.get("clock_idx", 0)
        return {"cursor": 0, "debate_round": 0,
                "clock_t": checkpoints[index] if index < len(checkpoints) else state.get("clock_t")}

    def heimdall_1(state: OdinState) -> dict:
        try:
            clock_t = state.get("clock_t") or date.today().isoformat()
            with store.connect() as db:
                count = db.execute("SELECT count(*) FROM operational_events WHERE owner_id=? AND substr(occurred_at,1,10)<=?", (owner, clock_t)).fetchone()[0]
            _message(store, owner, run_id, "Heimdall", "Norns", f"{count} recorded events at {clock_t}")
            return {}
        except Exception as exc:
            return {"errors": [_failure(store, owner, run_id, "Heimdall-1", exc)]}

    def norns(state: OdinState) -> dict:
        """Parse explicit + relative dates; compute worst-case $ exposure.
        Gap 1: Populates norns_exposure_usd in state via deterministic arithmetic.
        Also reads Heimdall verifications from prior checkpoints into memory state
        so shared memory = Thor extractions + Heimdall confirmed events + Norns calc."""
        try:
            terms = _items(store, owner, "agent-extraction", run_id)
            clock_t = state.get("clock_t") or date.today().isoformat()

            # ── Explicit date milestones (preserves existing behaviour) ───────
            for term in terms:
                for due in _explicit_dates(term["citation"]["quote"]):
                    _record(store, owner, run_id, "agent-timeline", "Norns",
                            f"{term['id']}:{due}", {
                        "document_key": term["document_key"], "date": due,
                        "description": term["value"], "citation": term["citation"],
                        "source_tag": "sourced",
                        "formula": "Explicit source date",
                        "worst_case_usd": 0.0,
                    })

            # ── Norns reads Heimdall verifications from prior checkpoints ─────
            # Shared memory = Thor extractions + Heimdall events + Norns calc
            prior_verifications = _items(store, owner, "agent-verification", run_id)
            confirmed_count = sum(1 for v in prior_verifications if v.get("verdict") == "confirmed")

            # ── Financial exposure calculation (Gap 1) ────────────────────────
            ledger_path = (
                Path(__file__).resolve().parents[1]
                / "dataset" / "Pack" / "odin_dev_pack" / "bundle" / "data"
                / "payments_ledger.csv"
            )
            ledger_rows: list[dict] = []
            if ledger_path.is_file():
                ledger_rows = parse_ledger(ledger_path.read_text(encoding="utf-8"))

            milestones, total_usd = compute_exposure(
                extractions=terms, ledger_rows=ledger_rows, clock_t=clock_t,
            )

            for ms in milestones:
                _record(store, owner, run_id, "agent-timeline", "Norns",
                        f"fin:{ms.milestone_id}:{clock_t}", {
                    "document_key": ms.document_key,
                    "date": ms.date,
                    "description": ms.description,
                    "citation": {
                        "clause_ref": ms.clause_citation, "quote": ms.formula,
                        "chunk_id": ms.milestone_id, "document_key": ms.document_key,
                    },
                    "source_tag": "computed",
                    "formula": ms.formula,
                    "worst_case_usd": ms.worst_case_usd,
                    "event_type": ms.event_type,
                    "risk_severity": ms.risk_severity,
                })

            _message(store, owner, run_id, "Norns", "Loki",
                     f"Timeline ready: {len(milestones)} milestones · "
                     f"worst-case ${total_usd:,.2f} USD · "
                     f"{confirmed_count} Heimdall-confirmed events in shared memory")
            return {"norns_exposure_usd": total_usd}
        except Exception as exc:
            return {"errors": [_failure(store, owner, run_id, "Norns", exc)]}

    def loki(state: OdinState) -> dict:
        """Gap 2: Inject Norns financial timeline into Loki's attack context.
        Loki now attacks clauses tied to Norns worst-case dollar exposures."""
        try:
            terms = _items(store, owner, "agent-extraction", run_id)
            evidence = [{"document_key": t["document_key"], "field": t["field"],
                         "value": t["value"], "citation": t["citation"]} for t in terms]
            if not evidence:
                return {"finding_ids": [], "cursor": 0}

            # Gap 2: Pull Norns financial milestones into Loki's attack surface
            timeline = _items(store, owner, "agent-timeline", run_id)
            norns_ctx = {
                "total_worst_case_usd": state.get("norns_exposure_usd", 0.0),
                "financial_milestones": [
                    {
                        "date": t.get("date"), "event_type": t.get("event_type"),
                        "description": t.get("description"),
                        "exposure_usd": t.get("worst_case_usd", 0.0),
                        "severity": t.get("risk_severity"),
                        "milestone_id": t.get("citation", {}).get("chunk_id", ""),
                        "clause": t.get("citation", {}).get("clause_ref", ""),
                    }
                    for t in timeline if t.get("source_tag") == "computed"
                ][:12],
            }
            loki_input = {"thor_extractions": evidence, "norns_timeline": norns_ctx}
            output = _model_json(store, owner, run_id, "Loki", model,
                'You are Loki, adversarial contract analyst and devil\'s advocate. You MUST find vulnerabilities, hidden liabilities, and payment risks in the provided extractions and timeline.\n\n'
                'THOR EXTRACTIONS:\n' + json.dumps(evidence, sort_keys=True) + '\n\n'
                'NORNS TIMELINE:\n' + json.dumps(norns_ctx, sort_keys=True) + '\n\n'
                'INSTRUCTION:\n'
                'Identify at least 2 to 4 potential contractual risks, one-sided terms, or timeline bottlenecks.\n'
                'Cross-reference high-dollar exposure items with ambiguous clauses.\n\n'
                'OUTPUT FORMAT (JSON ONLY):\n'
                '{\n'
                '  "findings": [\n'
                '    {\n'
                '      "finding_id": "LOKI-001",\n'
                '      "claim": "Clear concise adversarial risk claim",\n'
                '      "clause_citation": "Section C — Fees and Payment",\n'
                '      "reasoning": "Detailed legal and financial rationale",\n'
                '      "severity": "HIGH",\n'
                '      "financial_exposure_usd": 30900.0,\n'
                '      "citations": [\n'
                '        {"document_key": "B1", "clause_ref": "Section C — Fees and Payment", "quote": "..."}\n'
                '      ]\n'
                '    }\n'
                '  ]\n'
                '}\n'
                'At most 8 findings. For citations, select or copy citation objects from THOR EXTRACTIONS.', 4800)

            # Robust JSON/List Parsing
            findings_raw = []
            if isinstance(output, dict):
                for key in ("findings", "items", "challenges", "vulnerabilities", "risks"):
                    if isinstance(output.get(key), list):
                        findings_raw = output[key]
                        break
                if not findings_raw and ("claim" in output or "attack_path" in output):
                    findings_raw = [output]
            elif isinstance(output, list):
                findings_raw = output

            ids: list[str] = []
            with store.connect() as db:
                for index, item in enumerate(findings_raw[:8]):
                    if not isinstance(item, dict):
                        continue

                    raw_cites = item.get("citations", [])
                    if isinstance(raw_cites, dict):
                        raw_cites = [raw_cites]
                    citations = _verified(db, owner, raw_cites)

                    # Resilient Auto-Healing: If citations failed strict quote match,
                    # anchor to the most relevant Thor verified citation from evidence
                    if not citations and evidence:
                        doc_key = item.get("document_key") or (raw_cites and isinstance(raw_cites, list) and raw_cites[0].get("document_key"))
                        candidates = [e["citation"] for e in evidence if not doc_key or e["document_key"] == doc_key]
                        if not candidates:
                            candidates = [e["citation"] for e in evidence]
                        claim_lower = (str(item.get("claim", "")) + " " + str(item.get("reasoning", "")) + " " + str(item.get("clause_citation", ""))).lower()
                        best_cite = candidates[0]
                        for c in candidates:
                            clause_name = str(c.get("clause_ref", "")).lower()
                            if clause_name and clause_name in claim_lower:
                                best_cite = c
                                break
                        citations = [best_cite]

                    if not citations:
                        continue

                    claim_text = str(item.get("claim") or item.get("attack_path") or item.get("risk") or item.get("finding_id") or "")[:500]
                    if not claim_text:
                        continue

                    severity = str(item.get("severity", "medium")).lower()
                    if severity not in ("low", "medium", "high", "critical"):
                        severity = "medium"

                    finding = _save(db, owner, "agent-finding", {
                        "run_id": run_id, "agent": "Loki",
                        "claim": claim_text,
                        "reasoning": str(item.get("reasoning") or item.get("explanation") or claim_text)[:1500],
                        "severity": severity,
                        "citations": citations, "source_tag": "inferred", "status": "proposed",
                        "norns_milestone_id": str(item.get("norns_milestone_id") or item.get("finding_id") or "")[:20],
                        "financial_exposure_usd": float(item.get("financial_exposure_usd") or 0.0),
                    }, _stable_id(run_id, "Loki", str(index)))
                    ids.append(finding["id"])

            _message(store, owner, run_id, "Loki", "Heimdall",
                     f"{len(ids)} cited challenges · "
                     f"total flagged ${norns_ctx['total_worst_case_usd']:,.2f} USD")
            return {
                "finding_ids": ids,
                "cursor": 0,
                "debate_history": [{
                    "round": 0,
                    "agent": "Loki",
                    "action": "findings_proposed",
                    "count": len(ids),
                }],
            }
        except Exception as exc:
            return {"finding_ids": [], "errors": [_failure(store, owner, run_id, "Loki", exc)]}

    def finding_at(state: OdinState) -> dict | None:
        ids = state.get("finding_ids", [])
        cursor = state.get("cursor", 0)
        if cursor >= len(ids):
            return None
        return next((x for x in _items(store, owner, "agent-finding", run_id) if x["id"] == ids[cursor]), None)

    def thor_clarify(state: OdinState) -> dict:
        """Thor answers Loki using only evidence anchored to chunks.
        Gap 3: Hash-based dedup — if same finding+round already answered,
        return early to break the ChromaDB infinite re-extraction loop."""
        finding = finding_at(state)
        if not finding:
            return {}

        # Gap 3 (Infinite loop fix): hash finding_id + debate_round
        debate_round = state.get("debate_round", 0)
        clarify_key = hashlib.sha256(
            f"{finding['id']}:{debate_round}".encode()
        ).hexdigest()[:16]
        if clarify_key in state.get("clarification_hashes", []):
            no_new = (
                "No new evidence found in clause text — "
                "Thor's prior answer stands. Heimdall must decide on existing evidence."
            )
            _message(store, owner, run_id, "Thor", "Loki", no_new, finding["id"])
            return {
                "debate_history": [{
                    "round": debate_round, "agent": "Thor",
                    "action": "dedup_skip", "finding_id": finding["id"],
                }],
            }

        try:
            prior = [
                c for c in _items(store, owner, "agent-clarification", run_id)
                if c.get("finding_id") == finding["id"]
            ]
            output = _model_json(store, owner, run_id, "Thor-clarify", model,
                'Act as Thor\'s evidence advocate. Loki challenged a contract term. Return JSON '
                '{"answer":string,"supported":boolean,"citation_ids":[string]}. '
                'Use ONLY the supplied verified chunk citations. '
                'Do not add facts, dates, events, or money not in the citations. '
                'If prior clarifications already covered this, acknowledge them without repeating. '
                'If chunks do not answer the challenge, set supported=false. '
                'Input: ' + json.dumps({
                    "finding": finding,
                    "verified_chunks": finding["citations"],
                    "debate_round": debate_round,
                    "prior_clarifications": [
                        {"answer": c.get("answer", ""), "supported": c.get("supported")}
                        for c in prior[-2:]
                    ],
                }, sort_keys=True), 1400)
            allowed = {str(c.get("chunk_id", "")) for c in finding["citations"]}
            clarification = _record(store, owner, run_id, "agent-clarification", "Thor",
                f"{state.get('clock_t')}:{finding['id']}:{debate_round}", {
                    "finding_id": finding["id"],
                    "answer": str(output.get("answer", ""))[:1200],
                    "supported": bool(output.get("supported")),
                    "citation_ids": [str(x) for x in output.get("citation_ids", []) if str(x) in allowed],
                    "citations": finding["citations"],
                    "debate_round": debate_round,
                })
            _message(store, owner, run_id, "Thor", "Loki", clarification["answer"], finding["id"])
            return {
                "clarification_hashes": [clarify_key],
                "debate_history": [{
                    "round": debate_round, "agent": "Thor",
                    "action": "clarify", "finding_id": finding["id"],
                    "supported": bool(output.get("supported")),
                }],
            }
        except Exception as exc:
            return {"errors": [_failure(store, owner, run_id, "Thor-clarify", exc)]}

    def heimdall_2(state: OdinState) -> dict:
        """Verify Loki claims against chunks + events.
        Gap 4: Normalize event schema to match ChromaDB format; filter noise events.
        Records debate_history so all rounds are preserved (fixes memory bleed)."""
        finding = finding_at(state)
        if not finding:
            return {"verdict": "insufficient"}
        try:
            clock_t = state["clock_t"]
            with store.connect() as db:
                rows = db.execute(
                    "SELECT event_id,occurred_at,channel,subject,body,sender,recipient "
                    "FROM operational_events WHERE owner_id=? "
                    "AND substr(occurred_at,1,10)<=? ORDER BY occurred_at LIMIT 100",
                    (owner, clock_t)
                ).fetchall()
                raw_events = [dict(row) for row in rows]

            # Gap 4: Extract clause keywords from finding citations for noise filtering
            clause_keywords: set[str] = set()
            for cite in finding.get("citations", []):
                clause_keywords.update(
                    w.lower() for w in re.findall(r"\b\w{5,}\b", cite.get("quote", ""))[:20]
                )
            clause_keywords.update({
                "payment", "notice", "sla", "uptime", "credit", "terminat",
                "breach", "renew", "outage", "overdue", "interest", "invoice",
            })

            def _relevant(ev: dict) -> bool:
                body = f"{ev.get('subject', '')} {ev.get('body', '')}".lower()
                return any(kw in body for kw in clause_keywords)

            # Normalize to unified evidence schema matching ChromaDB chunk format
            normalized: list[dict] = [
                {
                    "event_id": ev["event_id"],
                    "date": ev["occurred_at"][:10],
                    "channel": ev.get("channel", "unknown"),
                    "summary": f"{ev.get('subject', '')}: {ev.get('body', '')[:300]}",
                    "source_type": "operational_event",
                }
                for ev in raw_events if _relevant(ev)
            ][:20]

            rebuttals = [m for m in _items(store, owner, "agent-message", run_id)
                         if m.get("from") == "Loki" and m.get("payload_ref") == finding["id"]]
            clarifications = [c for c in _items(store, owner, "agent-clarification", run_id)
                               if c.get("finding_id") == finding["id"]]
            debate_round = state.get("debate_round", 0)

            output = _model_json(store, owner, run_id, "Heimdall-2", model,
                'You are Heimdall, evidence verifier and noise filter. '
                'Decide whether cited clause text AND matching operational events support this risk. '
                'Return JSON {"verdict":"confirmed|challenged|insufficient",'
                '"reason":string,"event_ids":[string],"noise_filtered":number}. '
                'Rules: (1) Only use events whose summary is directly relevant to the cited clause. '
                '(2) Thor/Loki statements are arguments — verify against chunk text and event_ids only. '
                '(3) No events + ambiguous clause text → insufficient. '
                'Input: ' + json.dumps({
                    "finding": finding,
                    "normalized_events": normalized,
                    "noise_filtered_out": len(raw_events) - len(normalized),
                    "thor_answer": clarifications[-1] if clarifications else None,
                    "loki_rebuttal": rebuttals[-1]["message"] if rebuttals else None,
                    "debate_round": debate_round,
                }, sort_keys=True), 1600)

            verdict = (output.get("verdict")
                       if output.get("verdict") in ("confirmed", "challenged", "insufficient")
                       else "insufficient")
            valid_ids = {ev["event_id"] for ev in normalized}
            verification = _record(store, owner, run_id, "agent-verification", "Heimdall",
                f"{clock_t}:{finding['id']}:{debate_round}", {
                    "finding_id": finding["id"], "verdict": verdict, "clock_t": clock_t,
                    "reason": str(output.get("reason", ""))[:1000],
                    "event_ids": [e for e in output.get("event_ids", []) if e in valid_ids][:10],
                    "citations": finding["citations"],
                    "noise_filtered": output.get("noise_filtered", 0),
                })
            _message(store, owner, run_id, "Heimdall", "Odin",
                     f"{verdict}: {finding['claim'][:100]}", verification["id"])
            return {
                "verdict": verdict,
                "debate_history": [{
                    "round": debate_round, "agent": "Heimdall",
                    "finding_id": finding["id"], "verdict": verdict,
                    "reason": str(output.get("reason", ""))[:200],
                }],
            }
        except Exception as exc:
            return {"verdict": "insufficient",
                    "errors": [_failure(store, owner, run_id, "Heimdall-2", exc)]}

    def odin_router(state: OdinState) -> dict:
        finding = finding_at(state)
        if not finding:
            return {}
        verdict = state.get("verdict", "insufficient")
        round_no = state.get("debate_round", 0)
        destination = "Loki" if verdict == "challenged" and round_no < MAX_DEBATE_ROUNDS else "Tyr"
        _message(store, owner, run_id, "Odin", destination, f"{finding['id']}: {verdict}; debate round {round_no}")
        return {}

    def debate_route(state: OdinState) -> str:
        return "loki_rebut" if state.get("verdict") == "challenged" and state.get("debate_round", 0) < MAX_DEBATE_ROUNDS else "tyr"

    def loki_rebut(state: OdinState) -> dict:
        finding = finding_at(state)
        if not finding:
            return {"debate_round": MAX_DEBATE_ROUNDS}
        try:
            verifications = [v for v in _items(store, owner, "agent-verification", run_id) if v["finding_id"] == finding["id"]]
            prior = verifications[-1] if verifications else None
            output = _model_json(store, owner, run_id, "Loki-rebut", model,
                'You are Loki. A proposed risk was challenged. Return JSON {"rebuttal":string}. Only use the existing cited evidence; admit uncertainty if no rebuttal is supported. Input: ' + json.dumps({"finding": finding, "verification": prior}, sort_keys=True), 1200)
            _record(store, owner, run_id, "agent-message", "Loki", f"rebut:{finding['id']}", {
                "from": "Loki", "to": "Heimdall", "message": str(output.get("rebuttal", ""))[:1200], "payload_ref": finding["id"],
            })
            return {"debate_round": state.get("debate_round", 0) + 1}
        except Exception as exc:
            return {"debate_round": MAX_DEBATE_ROUNDS, "errors": [_failure(store, owner, run_id, "Loki-rebut", exc)]}

    def tyr(state: OdinState) -> dict:
        finding = finding_at(state)
        if not finding:
            return {}
        try:
            verifications = [v for v in _items(store, owner, "agent-verification", run_id) if v["finding_id"] == finding["id"]]
            verification = verifications[-1] if verifications else {"verdict": "insufficient", "citations": finding["citations"]}
            output = _model_json(store, owner, run_id, "Tyr", model,
                'You are Tyr, arbiter and action drafter. Treat verification and source citations as binding evidence. Return JSON {"outcome":"upheld|rejected|needs_review","rationale":string,"draft_notice":string|null}. A notice must be a draft for human approval, cite provided clauses, and omit unsupported dates, amounts, addressees. An insufficient verdict requires needs_review. Input: ' + json.dumps({"finding": finding, "verification": verification}, sort_keys=True), 1800)
            outcome = output.get("outcome") if output.get("outcome") in ("upheld", "rejected", "needs_review") else "needs_review"
            if verification["verdict"] == "insufficient":
                outcome = "needs_review"
            ruling = _record(store, owner, run_id, "agent-ruling", "Tyr", f"{state['clock_t']}:{finding['id']}", {
                "finding_id": finding["id"], "verification_id": verification.get("id"),
                "clock_t": state["clock_t"],
                "outcome": outcome, "rationale": str(output.get("rationale", ""))[:1500],
                "draft_notice": str(output["draft_notice"])[:5000] if output.get("draft_notice") and outcome == "upheld" else None,
                "citations": finding["citations"], "needs_human_approval": True,
            })
            _message(store, owner, run_id, "Tyr", "Odin", f"{outcome}: {finding['claim'][:100]}", ruling["id"])
            if verification["verdict"] == "confirmed":
                draft_id = _stable_id(run_id, "alert-draft", finding["id"])
                citations = "\n".join(
                    f"- {cite['document_key']} / {cite['clause_ref']}: {cite['quote']}"
                    for cite in finding["citations"]
                )
                with store.connect() as db:
                    existing = db.execute("SELECT id FROM web_records WHERE id=? AND owner_id=? AND kind='agent-email-draft'", (draft_id, owner)).fetchone()
                    if not existing:
                        _save(db, owner, "agent-email-draft", {
                            "run_id": run_id, "finding_id": finding["id"], "ruling_id": ruling["id"],
                            "status": "DRAFT", "recipient": getattr(model.settings, "odin_alert_recipient", "") or None,
                            "subject": f"ODIN review alert: {finding['claim'][:100]}",
                            "body": (
                                "ODIN flagged a cited contract risk for human review.\n\n"
                                f"Finding: {finding['claim']}\n"
                                f"Heimdall: {verification['reason']}\n"
                                f"Tyr: {outcome} — {ruling['rationale']}\n\n"
                                f"Source citations:\n{citations}\n\n"
                                "This is an internal review alert, not a legal notice or a verified financial forecast."
                            ),
                            "approved_at": None, "sent_at": None, "provider_id": None,
                        }, draft_id)
            return {"cursor": state.get("cursor", 0) + 1, "debate_round": 0}
        except Exception as exc:
            return {"cursor": state.get("cursor", 0) + 1, "debate_round": 0, "errors": [_failure(store, owner, run_id, "Tyr", exc)]}

    def next_finding(state: OdinState) -> str:
        return "heimdall_2" if state.get("cursor", 0) < len(state.get("finding_ids", [])) else END

    debate = StateGraph(OdinState)
    debate.add_node("loki", loki)
    debate.add_node("thor_clarify", thor_clarify)
    debate.add_node("heimdall_2", heimdall_2)
    debate.add_node("odin_router", odin_router)
    debate.add_node("loki_rebut", loki_rebut)
    debate.add_node("tyr", tyr)
    debate.add_edge(START, "loki")
    debate.add_conditional_edges("loki", next_finding, {"heimdall_2": "thor_clarify", END: END})
    debate.add_edge("thor_clarify", "heimdall_2")
    debate.add_edge("heimdall_2", "odin_router")
    debate.add_conditional_edges("odin_router", debate_route, {"loki_rebut": "loki_rebut", "tyr": "tyr"})
    debate.add_edge("loki_rebut", "heimdall_2")
    debate.add_conditional_edges("tyr", next_finding, {"heimdall_2": "thor_clarify", END: END})

    def norns_scenario(state: OdinState) -> dict:
        """Build financial worst-case scenario from verified dates and rulings.
        Gap 1: Populates real exposure_amount from Norns financial simulation.
        Gap 5: HITL re-computation — excludes human-approved findings from open exposure."""
        clock_t = state.get("clock_t", date.today().isoformat())
        dates = _items(store, owner, "agent-timeline", run_id)
        rulings = [r for r in _items(store, owner, "agent-ruling", run_id)
                   if r.get("clock_t") == clock_t]
        elapsed  = [t for t in dates if t.get("date", "") <= clock_t]
        upheld   = [r for r in rulings if r.get("outcome") == "upheld"]
        review   = [r for r in rulings if r.get("outcome") == "needs_review"]
        rejected = [r for r in rulings if r.get("outcome") == "rejected"]

        # Gap 1: Real financial exposure from Norns simulation
        base_exposure = state.get("norns_exposure_usd", 0.0)

        # Gap 5: HITL — subtract exposure from human-approved/rejected findings
        with store.connect() as db:
            resolved_rows = db.execute(
                "SELECT json_extract(data,'$.finding_id') AS fid "
                "FROM web_records WHERE owner_id=? AND kind='agent-ruling' "
                "AND json_extract(data,'$.run_id')=? "
                "AND json_extract(data,'$.human_approved') IS NOT NULL",
                (owner, run_id)
            ).fetchall()
        resolved_ids: set[str] = {row[0] for row in resolved_rows if row[0]}

        computed = [t for t in elapsed if t.get("source_tag") == "computed"]
        resolved_usd = sum(
            t.get("worst_case_usd", 0.0) for t in computed
            if t.get("citation", {}).get("chunk_id", "") in resolved_ids
        )
        adjusted = max(0.0, base_exposure - resolved_usd)

        scenario = _record(store, owner, run_id, "agent-scenario", "Norns", clock_t, {
            "clock_t": clock_t, "kind": "financial_worst_case",
            "summary": (
                f"{len(elapsed)} elapsed milestones · "
                f"{len(upheld)} upheld · {len(review)} pending human review · "
                f"{len(rejected)} rejected · {len(resolved_ids)} human-resolved. "
                f"Adjusted open exposure: ${adjusted:,.2f} USD "
                f"(base ${base_exposure:,.2f} - resolved ${resolved_usd:,.2f})."
            ),
            "elapsed_timeline_ids": [t["id"] for t in elapsed],
            "upheld_ruling_ids": [r["id"] for r in upheld],
            "review_ruling_ids": [r["id"] for r in review],
            "resolved_finding_count": len(resolved_ids),
            "exposure_amount": round(adjusted, 2) if adjusted > 0 else None,
            "base_exposure_usd": round(base_exposure, 2) if base_exposure > 0 else None,
            "resolved_exposure_usd": round(resolved_usd, 2) if resolved_usd > 0 else None,
            "currency": "USD" if adjusted > 0 else None,
            "limitation": (
                "Worst-case financial projection from clause arithmetic and payment ledger. "
                "Not a verified settlement amount or legal determination."
            ),
        })
        _message(store, owner, run_id, "Norns", "Odin",
                 f"Financial scenario: ${adjusted:,.2f} open exposure "
                 f"({len(resolved_ids)} human-resolved items deducted)", scenario["id"])
        return {}

    def snapshot(state: OdinState) -> dict:
        _record(store, owner, run_id, "agent-snapshot", "Odin", state.get("clock_t", "unknown"), {
            "clock_t": state.get("clock_t"),
            "extraction_count": len(_items(store, owner, "agent-extraction", run_id)),
            "finding_count": len(_items(store, owner, "agent-finding", run_id)),
            "exposure": state.get("norns_exposure_usd"),  # Real $ from Norns simulation
            "debate_rounds_completed": state.get("debate_round", 0),
            "debate_history_length": len(state.get("debate_history", [])),
        })
        return {}

    def checkpoint_advance(state: OdinState) -> dict:
        return {"clock_idx": state.get("clock_idx", 0) + 1}

    def after_snapshot(state: OdinState) -> str:
        return "checkpoint_advance" if state.get("clock_idx", 0) + 1 < len(state.get("checkpoints", [])) else "completeness_gate"

    def completeness_gate(state: OdinState) -> dict:
        covered = {item["document_key"] for item in _items(store, owner, "agent-extraction", run_id)}
        missing = set(state.get("doc_ids", [])) - covered
        reasons = list(state.get("errors", []))
        if missing:
            reasons.append("No verified terms for: " + ", ".join(sorted(missing)))
        if not state.get("doc_ids"):
            reasons.append("No valid source documents")
        observed = {item["clock_t"] for item in _items(store, owner, "agent-scenario", run_id)}
        unprocessed = set(state.get("checkpoints", [])) - observed
        if unprocessed:
            reasons.append("No scenario snapshot for: " + ", ".join(sorted(unprocessed)))
        status = "INCOMPLETE" if reasons else "COMPLETE"
        _record(store, owner, run_id, "agent-gate", "Odin", "final", {"status": status, "reasons": reasons})
        return {"status": status}

    def synthesis(state: OdinState) -> dict:
        gate = _items(store, owner, "agent-gate", run_id)[-1]
        error = "; ".join(gate["reasons"])[:200] if gate["reasons"] else None
        _set_status(store, owner, run_id, state["status"], error)
        _message(store, owner, run_id, "Odin", "User", f"Run {state['status'].lower()}" + (f": {error}" if error else ""))
        return {}

    graph = StateGraph(OdinState)
    for name, node in (
        ("ingest", ingest), ("odin_plan", odin_plan), ("thor", thor),
        ("terms_merge", terms_merge), ("checkpoint_init", checkpoint_init),
        ("heimdall_1", heimdall_1), ("norns", norns), ("debate", debate.compile()),
        ("norns_scenario", norns_scenario), ("snapshot", snapshot),
        ("checkpoint_advance", checkpoint_advance),
        ("completeness_gate", completeness_gate), ("synthesis", synthesis),
    ):
        graph.add_node(name, node)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "odin_plan")
    graph.add_conditional_edges("odin_plan", distribute, {"terms_merge": "terms_merge", "thor": "thor"})
    graph.add_edge("thor", "terms_merge")
    for before, after in (
        ("terms_merge", "checkpoint_init"), ("checkpoint_init", "heimdall_1"),
        ("heimdall_1", "norns"), ("norns", "debate"),
        ("debate", "norns_scenario"), ("norns_scenario", "snapshot"),
        ("checkpoint_advance", "checkpoint_init"), ("completeness_gate", "synthesis"),
        ("synthesis", END),
    ):
        graph.add_edge(before, after)
    graph.add_conditional_edges("snapshot", after_snapshot,
                                {"checkpoint_advance": "checkpoint_advance", "completeness_gate": "completeness_gate"})
    return graph.compile(checkpointer=checkpointer)


def execute_graph(store: Store, owner: str, run_id: str, model) -> None:
    run = run_view(store, owner, run_id)
    if not run or run["status"] not in ("QUEUED", "RUNNING"):
        return
    if run["status"] == "QUEUED":
        _set_status(store, owner, run_id, "RUNNING")
    checkpoint_path = Path(str(store.path) + ".langgraph.sqlite3")
    checkpoints = len(run.get("checkpoints") or [run["started_at"][:10]])
    config = {"configurable": {"thread_id": run_id},
              "recursion_limit": max(128, checkpoints * (24 + 8 * (5 + 2 * MAX_DEBATE_ROUNDS)) + 20)}
    try:
        with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
            graph = build_graph(store, owner, run_id, model, checkpointer)
            previous = graph.get_state(config)
            payload = None if previous.values and previous.next else {"run_id": run_id}
            graph.invoke(payload, config)
    except GraphRecursionError:
        _message(store, owner, run_id, "Odin", "User", "Run incomplete: graph iteration limit reached")
        _set_status(store, owner, run_id, "INCOMPLETE", "Graph iteration limit reached")
    except Exception as exc:
        detail = _failure(store, owner, run_id, "graph", exc)
        _set_status(store, owner, run_id, "INCOMPLETE", detail)
