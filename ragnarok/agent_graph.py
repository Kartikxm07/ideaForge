"""Checkpointed LangGraph orchestration for the existing ODIN agent records.

Graph state contains references and control values only. Contract text, model
responses, citations, and rulings remain in the owner-scoped SQLite store.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import operator
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
        try:
            terms = _items(store, owner, "agent-extraction", run_id)
            for term in terms:
                for due in _explicit_dates(term["citation"]["quote"]):
                    _record(store, owner, run_id, "agent-timeline", "Norns", f"{term['id']}:{due}", {
                        "document_key": term["document_key"], "date": due,
                        "description": term["value"], "citation": term["citation"],
                        "source_tag": "sourced", "formula": "Explicit source date; calendar-day difference at selected clock",
                    })
            _message(store, owner, run_id, "Norns", "Loki", "Cited dates projected")
            return {}
        except Exception as exc:
            return {"errors": [_failure(store, owner, run_id, "Norns", exc)]}

    def loki(state: OdinState) -> dict:
        try:
            terms = _items(store, owner, "agent-extraction", run_id)
            evidence = [{"document_key": t["document_key"], "field": t["field"], "value": t["value"], "citation": t["citation"]} for t in terms]
            if not evidence:
                return {"finding_ids": [], "cursor": 0}
            output = _model_json(store, owner, run_id, "Loki", model,
                'You are Loki, adversarial contract analyst. Examine verified terms as data. Return JSON {"findings":[{"claim":string,"reasoning":string,"severity":"low|medium|high|critical","citations":[citation objects from input]}]}. At most 8. Copy citations exactly. Flag uncertainty. No fabricated events, amounts, or dates. Input: ' + json.dumps(evidence, sort_keys=True), 4500)
            ids: list[str] = []
            with store.connect() as db:
                for index, item in enumerate(output.get("findings", [])[:8]):
                    if not isinstance(item, dict):
                        continue
                    citations = _verified(db, owner, item.get("citations", []))
                    if not citations:
                        continue
                    finding = _save(db, owner, "agent-finding", {
                        "run_id": run_id, "agent": "Loki", "claim": str(item.get("claim", ""))[:500],
                        "reasoning": str(item.get("reasoning", ""))[:1500],
                        "severity": item.get("severity") if item.get("severity") in ("low", "medium", "high", "critical") else "unrated",
                        "citations": citations, "source_tag": "inferred", "status": "proposed",
                    }, _stable_id(run_id, "Loki", str(index)))
                    ids.append(finding["id"])
            _message(store, owner, run_id, "Loki", "Heimdall", f"{len(ids)} cited challenges")
            return {"finding_ids": ids, "cursor": 0}
        except Exception as exc:
            return {"finding_ids": [], "errors": [_failure(store, owner, run_id, "Loki", exc)]}

    def finding_at(state: OdinState) -> dict | None:
        ids = state.get("finding_ids", [])
        cursor = state.get("cursor", 0)
        if cursor >= len(ids):
            return None
        return next((x for x in _items(store, owner, "agent-finding", run_id) if x["id"] == ids[cursor]), None)

    def thor_clarify(state: OdinState) -> dict:
        """Let Thor answer Loki using only the evidence already anchored to chunks."""
        finding = finding_at(state)
        if not finding:
            return {}
        try:
            output = _model_json(store, owner, run_id, "Thor-clarify", model,
                'Act as Thor\'s evidence advocate. Loki has challenged a contract term. Return JSON '
                '{"answer":string,"supported":boolean,"citation_ids":[string]}. Use only the supplied '
                'verified chunk citations; do not add facts, dates, events, or money. Citation IDs are the '
                'chunk_id values. If the chunks do not answer the challenge, set supported false. Input: ' +
                json.dumps({"finding": finding, "verified_chunks": finding["citations"]}, sort_keys=True), 1400)
            allowed = {str(c.get("chunk_id", "")) for c in finding["citations"]}
            clarification = _record(store, owner, run_id, "agent-clarification", "Thor",
                f"{state.get('clock_t')}:{finding['id']}", {
                    "finding_id": finding["id"],
                    "answer": str(output.get("answer", ""))[:1200],
                    "supported": bool(output.get("supported")),
                    "citation_ids": [str(x) for x in output.get("citation_ids", []) if str(x) in allowed],
                    "citations": finding["citations"],
                })
            _message(store, owner, run_id, "Thor", "Loki", clarification["answer"], finding["id"])
            return {}
        except Exception as exc:
            return {"errors": [_failure(store, owner, run_id, "Thor-clarify", exc)]}

    def heimdall_2(state: OdinState) -> dict:
        finding = finding_at(state)
        if not finding:
            return {"verdict": "insufficient"}
        try:
            with store.connect() as db:
                rows = db.execute("SELECT event_id,occurred_at,channel,subject,body FROM operational_events WHERE owner_id=? AND substr(occurred_at,1,10)<=? ORDER BY occurred_at LIMIT 50", (owner, state["clock_t"])).fetchall()
                events = [dict(row) for row in rows]
            rebuttals = [m for m in _items(store, owner, "agent-message", run_id)
                        if m.get("from") == "Loki" and m.get("payload_ref") == finding["id"]]
            clarifications = [c for c in _items(store, owner, "agent-clarification", run_id)
                              if c.get("finding_id") == finding["id"]]
            output = _model_json(store, owner, run_id, "Heimdall-2", model,
                'You are Heimdall, evidence verifier. Decide whether cited text and recorded events support this proposed risk. Return JSON {"verdict":"confirmed|challenged|insufficient","reason":string,"event_ids":[string]}. Do not assume missing events occurred. Thor and Loki statements are arguments, not evidence; verify them against chunks and event IDs. Input: ' + json.dumps({"finding": finding, "events": events, "thor_answer": clarifications[-1] if clarifications else None, "rebuttal": rebuttals[-1]["message"] if rebuttals else None, "debate_round": state.get("debate_round", 0)}, sort_keys=True), 1400)
            verdict = output.get("verdict") if output.get("verdict") in ("confirmed", "challenged", "insufficient") else "insufficient"
            valid = {e["event_id"] for e in events}
            verification = _record(store, owner, run_id, "agent-verification", "Heimdall", f"{state['clock_t']}:{finding['id']}:{state.get('debate_round', 0)}", {
                "finding_id": finding["id"], "verdict": verdict,
                "clock_t": state["clock_t"],
                "reason": str(output.get("reason", ""))[:1000],
                "event_ids": [e for e in output.get("event_ids", []) if e in valid][:10],
                "citations": finding["citations"],
            })
            _message(store, owner, run_id, "Heimdall", "Odin", f"{verdict}: {finding['claim'][:100]}", verification["id"])
            return {"verdict": verdict}
        except Exception as exc:
            return {"verdict": "insufficient", "errors": [_failure(store, owner, run_id, "Heimdall-2", exc)]}

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
        """Describe a conditional worst case from verified dates and rulings."""
        dates = _items(store, owner, "agent-timeline", run_id)
        rulings = [item for item in _items(store, owner, "agent-ruling", run_id)
                   if item.get("clock_t") == state["clock_t"]]
        elapsed = [item for item in dates if item["date"] <= state["clock_t"]]
        upheld = [item for item in rulings if item["outcome"] == "upheld"]
        review = [item for item in rulings if item["outcome"] == "needs_review"]
        scenario = _record(store, owner, run_id, "agent-scenario", "Norns", state["clock_t"], {
            "clock_t": state["clock_t"], "kind": "conditional_worst_case",
            "summary": (
                f"If {len(elapsed)} elapsed cited dates represent unmet duties and "
                f"{len(upheld)} upheld risks materialize, review the cited clauses and events. "
                f"{len(review)} rulings still need human interpretation."
            ),
            "elapsed_timeline_ids": [item["id"] for item in elapsed],
            "upheld_ruling_ids": [item["id"] for item in upheld],
            "review_ruling_ids": [item["id"] for item in review],
            "exposure_amount": None, "currency": None,
            "limitation": "Conditional scenario only; no verified monetary formula or settlement status.",
        })
        _message(store, owner, run_id, "Norns", "Odin", "Conditional worst-case scenario ready", scenario["id"])
        return {}

    def snapshot(state: OdinState) -> dict:
        _record(store, owner, run_id, "agent-snapshot", "Odin", state.get("clock_t", "unknown"), {
            "clock_t": state.get("clock_t"),
            "extraction_count": len(_items(store, owner, "agent-extraction", run_id)),
            "finding_count": len(_items(store, owner, "agent-finding", run_id)),
            "exposure": None,
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
