"""Bounded, evidence-checked contract hypotheses from local source text."""
from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
import uuid
from typing import Protocol
from pydantic import BaseModel, ConfigDict, Field
from .documents import _heading_at, verify_citation
from .store import Store, now


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_key: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    clause_ref: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=1000)


class CandidateFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=2000)
    evidence: list[Evidence] = Field(min_length=1, max_length=4)


class FindingBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[CandidateFinding] = Field(max_length=10)


class FindingProvider(Protocol):
    def propose_findings(self, question: str, contexts: list[dict]) -> FindingBatch: ...


def _excerpts(content: str, focus: str) -> list[dict]:
    snippets = []
    for match in list(re.finditer(re.escape(focus), content, re.IGNORECASE))[:4]:
        start = max(0, match.start() - 350)
        end = min(len(content), match.end() + 650)
        snippets.append({"heading": _heading_at(content, match.start()), "text": content[start:end], "match_offset": match.start() - start})
    return snippets


def run_view(db: sqlite3.Connection, owner_id: str, run_id: str) -> dict | None:
    row = db.execute("SELECT * FROM analysis_runs WHERE id=? AND owner_id=?", (run_id, owner_id)).fetchone()
    if row is None:
        return None
    findings = db.execute("SELECT id,ordinal,claim,explanation,evidence_json,status,created_at FROM findings WHERE run_id=? AND owner_id=? ORDER BY ordinal", (run_id, owner_id)).fetchall()
    return {
        "id": row["id"], "question": row["question"], "focus": row["focus"],
        "document_keys": json.loads(row["document_keys_json"]), "provider_kind": row["provider_kind"], "status": row["status"],
        "error": row["error"], "rejected_count": row["rejected_count"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "findings": [{"id": f["id"], "ordinal": f["ordinal"], "claim": f["claim"],
                      "explanation": f["explanation"], "evidence": json.loads(f["evidence_json"]),
                      "status": f["status"], "created_at": f["created_at"]} for f in findings],
    }


def create_run(store: Store, owner_id: str, question: str, focus: str, keys: list[str], idempotency_key: str | None = None, provider_kind: str = "ollama") -> dict:
    if not 1 <= len(question) <= 500 or not 2 <= len(focus) <= 100:
        raise ValueError("Question or focus is outside its allowed length")
    if not 1 <= len(keys) <= 3 or len(set(keys)) != len(keys):
        raise ValueError("Select 1 to 3 distinct source documents")
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", key) for key in keys):
        raise ValueError("Invalid document key")
    if provider_kind not in {"anthropic", "ollama", "deterministic"}:
        raise ValueError("Unsupported analysis provider")
    if provider_kind == "deterministic" and (len(keys) != 2 or "uptime" not in focus.casefold()):
        raise ValueError("Deterministic analysis currently compares uptime text in exactly two documents")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            prior = db.execute("SELECT id,question,focus,document_keys_json,provider_kind FROM analysis_runs WHERE owner_id=? AND idempotency_key=?", (owner_id, idempotency_key)).fetchone()
            if prior:
                if (prior["question"], prior["focus"], json.loads(prior["document_keys_json"]), prior["provider_kind"]) != (question, focus, keys, provider_kind):
                    raise ValueError("Idempotency key was already used for a different analysis")
                return run_view(db, owner_id, prior["id"])
        hashes = {}
        for key in keys:
            row = db.execute("SELECT content,content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner_id, key)).fetchone()
            if row is None:
                raise LookupError(f"Source document not found: {key}")
            if not _excerpts(row["content"], focus):
                raise ValueError(f"Focus text was not found in source: {key}")
            hashes[key] = row["content_sha256"]
        run_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO analysis_runs(id,owner_id,question,focus,document_keys_json,document_hashes_json,provider_kind,idempotency_key,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, owner_id, question, focus, json.dumps(keys), json.dumps(hashes), provider_kind, idempotency_key, "READY", now(), now()),
        )
        Store.audit(db, owner_id, "analysis.create", run_id, "allowed")
        return run_view(db, owner_id, run_id)


def cancel_run(store: Store, owner_id: str, run_id: str) -> dict | None:
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT status FROM analysis_runs WHERE id=? AND owner_id=?", (run_id, owner_id)).fetchone()
        if row is None:
            return None
        if row["status"] != "READY":
            raise ValueError("Only queued analyses can be cancelled")
        db.execute("UPDATE analysis_runs SET status='CANCELLED',updated_at=? WHERE id=? AND owner_id=?", (now(), run_id, owner_id))
        Store.audit(db, owner_id, "analysis.cancel", run_id, "allowed")
        return run_view(db, owner_id, run_id)


class DeterministicFindingProvider:
    """Narrow offline comparison of percentages in uptime commitment clauses."""

    def propose_findings(self, question: str, contexts: list[dict]) -> FindingBatch:
        if len(contexts) != 2:
            return FindingBatch(findings=[])
        values = []
        for context in contexts:
            chosen = None
            for excerpt in context["excerpts"]:
                heading = excerpt["heading"] or ""
                if "uptime" not in heading.casefold() or "commitment" not in heading.casefold():
                    continue
                text = excerpt["text"]
                match = re.search(r"\b\d{1,3}(?:\.\d+)?\s*%", text[excerpt["match_offset"]:])
                if match is None:
                    continue
                offset = excerpt["match_offset"] + match.start()
                line_start = text.rfind("\n", 0, offset) + 1
                line_end = text.find("\n", offset)
                quote = text[line_start:line_end if line_end >= 0 else len(text)].strip()
                if not quote or len(quote) > 1000:
                    continue
                quote_heading = _heading_at(text, offset) or heading
                chosen = (match.group().replace(" ", ""), Evidence(document_key=context["document_key"], clause_ref=quote_heading, quote=quote))
                break
            if chosen is None:
                return FindingBatch(findings=[])
            values.append(chosen)
        if values[0][0] == values[1][0]:
            return FindingBatch(findings=[])
        first, second = contexts[0]["document_key"], contexts[1]["document_key"]
        return FindingBatch(findings=[CandidateFinding(
            claim=f"Different uptime percentages appear in {first} and {second}",
            explanation=(f"The cited uptime sections contain {values[0][0]} and {values[1][0]}. "
                         "Review amendments, definitions, exclusions, and effective dates before treating this as a contractual conflict."),
            evidence=[values[0][1], values[1][1]],
        )])


def run_analysis_once(store: Store, owner_id: str, provider: FindingProvider) -> bool:
    """Claim one run and persist only findings whose citations match current sources."""
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM analysis_runs WHERE owner_id=? AND status IN ('READY','RUNNING') "
            "AND (lease_until IS NULL OR lease_until<?) ORDER BY created_at LIMIT 1",
            (owner_id, now()),
        ).fetchone()
        if row is None:
            return False
        run_id = row["id"]
        keys = json.loads(row["document_keys_json"])
        expected = json.loads(row["document_hashes_json"])
        contexts = []
        for key in keys:
            document = db.execute("SELECT content,content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner_id, key)).fetchone()
            if document is None or document["content_sha256"] != expected[key]:
                db.execute("UPDATE analysis_runs SET status='STALE',error='SourceChanged',lease_until=NULL,updated_at=? WHERE id=?", (now(), run_id))
                return True
            contexts.append({"document_key": key, "content_sha256": expected[key], "excerpts": _excerpts(document["content"], row["focus"])})
        lease = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat()
        claim_id = str(uuid.uuid4())
        db.execute("UPDATE analysis_runs SET status='RUNNING',lease_until=?,claim_id=?,updated_at=? WHERE id=?", (lease, claim_id, now(), run_id))

    try:
        active_provider = DeterministicFindingProvider() if row["provider_kind"] == "deterministic" else provider
        batch = active_provider.propose_findings(row["question"], contexts)
        if not isinstance(batch, FindingBatch):
            batch = FindingBatch.model_validate(batch)
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT status,claim_id FROM analysis_runs WHERE id=? AND owner_id=?", (run_id, owner_id)).fetchone()
            if current is None or current["status"] != "RUNNING" or current["claim_id"] != claim_id:
                return True
            for key in keys:
                document = db.execute("SELECT content_sha256 FROM documents WHERE owner_id=? AND document_key=?", (owner_id, key)).fetchone()
                if document is None or document["content_sha256"] != expected[key]:
                    db.execute("UPDATE analysis_runs SET status='STALE',error='SourceChanged',lease_until=NULL,claim_id=NULL,updated_at=? WHERE id=? AND claim_id=?", (now(), run_id, claim_id))
                    return True
            db.execute("DELETE FROM findings WHERE run_id=? AND owner_id=?", (run_id, owner_id))
            rejected = 0
            accepted = 0
            for candidate in batch.findings:
                checked = []
                for evidence in candidate.evidence:
                    if evidence.document_key not in keys:
                        checked = []
                        break
                    verdict = verify_citation(db, owner_id, evidence.document_key, evidence.clause_ref, evidence.quote)
                    if not verdict["verified"]:
                        checked = []
                        break
                    checked.append({**evidence.model_dump(), "content_sha256": verdict["content_sha256"], "offset": verdict["offset"]})
                if len(checked) != len(candidate.evidence):
                    rejected += 1
                    continue
                db.execute(
                    "INSERT INTO findings(id,run_id,owner_id,ordinal,claim,explanation,evidence_json,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), run_id, owner_id, accepted, candidate.claim, candidate.explanation, json.dumps(checked), "EVIDENCE_CHECKED", now()),
                )
                accepted += 1
            db.execute("UPDATE analysis_runs SET status='COMPLETED',error=NULL,rejected_count=?,lease_until=NULL,claim_id=NULL,updated_at=? WHERE id=? AND claim_id=?", (rejected, now(), run_id, claim_id))
            Store.audit(db, owner_id, "analysis.complete", run_id, "allowed")
        return True
    except Exception as exc:
        with store.connect() as db:
            changed = db.execute("UPDATE analysis_runs SET status='FAILED',error=?,lease_until=NULL,claim_id=NULL,updated_at=? WHERE id=? AND owner_id=? AND claim_id=?", (type(exc).__name__, now(), run_id, owner_id, claim_id)).rowcount
            if changed:
                Store.audit(db, owner_id, "analysis.complete", run_id, "failed")
        return True
