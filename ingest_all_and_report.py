"""
Master ingestion + LLM report + email script.
Reads ALL PDFs, TXTs, JSONLs from dataset/
Saves full content + rag_chunks into the demo org
Calls GPT-OSS-120b via OpenRouter to generate a full analysis report
Sends email report via Resend API to atharvmanojshukla7@gmail.com
"""
import sys, os, json, sqlite3, uuid, hashlib, re, requests
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR      = Path(__file__).parent
DATASET_DIR   = BASE_DIR / "dataset" / "Pack" / "odin_dev_pack" / "bundle"
ODIN_PS_PDF   = BASE_DIR / "dataset" / "Odin_PS.pdf"
DB_PATH       = BASE_DIR / "data" / "ragnarok.sqlite3"
DEMO_ORG_ID   = "48bb8512-ace0-4ee5-a8a6-6965bac7939a"

CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

def load_env():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL           = os.environ.get("MODEL_HEAVY", "openai/gpt-oss-120b")
RESEND_API_KEY  = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM     = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
EMAIL_TO        = "atharvmanojshukla7@gmail.com"

print(f"Connected to DB: {DB_PATH}")
print(f"Demo org: {DEMO_ORG_ID}")
print(f"Model: {MODEL}")
print(f"Email to: {EMAIL_TO}")
print()

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

def sha256h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def chunk_text(text):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start+CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def upsert_document(doc_key, title, content, source):
    existing = conn.execute(
        "SELECT id FROM documents WHERE owner_id=? AND document_key=?",
        (DEMO_ORG_ID, doc_key)
    ).fetchone()
    sha = sha256h(content)
    t = now_iso()
    if existing:
        doc_id = existing[0]
        conn.execute(
            "UPDATE documents SET title=?, content=?, content_sha256=?, source=?, updated_at=? WHERE id=?",
            (title, content, sha, source, t, doc_id)
        )
        print(f"  [doc] UPDATED  {doc_key} ({len(content)} chars)")
    else:
        doc_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO documents(id,owner_id,document_key,title,content,content_sha256,source,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (doc_id, DEMO_ORG_ID, doc_key, title, content, sha, source, t, t)
        )
        print(f"  [doc] INSERTED {doc_key} ({len(content)} chars)")
    return doc_id

def upsert_rag_chunks(doc_key, content):
    conn.execute("DELETE FROM rag_chunks WHERE owner_id=? AND document_key=?", (DEMO_ORG_ID, doc_key))
    t = now_iso()
    count = 0
    for i, chunk in enumerate(chunk_text(content)):
        chunk = chunk.strip()
        if not chunk:
            continue
        conn.execute(
            "INSERT INTO rag_chunks(id,owner_id,document_key,chunk_index,token_count,text,embedding,created_at)"
            " VALUES(?,?,?,?,?,?,NULL,?)",
            (str(uuid.uuid4()), DEMO_ORG_ID, doc_key, i, len(chunk)//4, chunk, t)
        )
        count += 1
    print(f"  [rag] {count} chunks for {doc_key}")
    return count

def upsert_event(event, source_file):
    eid = event.get("event_id", sha256h(event.get("body",""))[:8])
    if conn.execute("SELECT id FROM operational_events WHERE owner_id=? AND event_id=?", (DEMO_ORG_ID, eid)).fetchone():
        return False
    conn.execute(
        "INSERT INTO operational_events(id,owner_id,event_id,occurred_at,channel,sender,recipient,subject,body,content_sha256,source,imported_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), DEMO_ORG_ID, eid,
         event.get("timestamp", now_iso()), event.get("channel","unknown"),
         event.get("from",""), event.get("to",""), event.get("subject",""),
         event.get("body",""), sha256h(event.get("body","")), source_file, now_iso())
    )
    return True

# ── PHASE 1: TXT contracts ────────────────────────────────────────────────────
print("=" * 60)
print("PHASE 1: Ingesting TXT contract files")
print("=" * 60)

txt_files = {
    "context": (DATASET_DIR/"company"/"context.txt",   "Quillhub Inc. Company Context"),
    "STD":     (DATASET_DIR/"contracts"/"STD.txt",      "Common Paper CSA Standard Terms v2.0"),
    "A1":      (DATASET_DIR/"contracts"/"A1.txt",       "CSA Cover Page — StratoNode Inc."),
    "A2":      (DATASET_DIR/"contracts"/"A2.txt",       "StratoNode CloudCore Service Level Agreement"),
    "A3":      (DATASET_DIR/"contracts"/"A3.txt",       "Amendment No.1 to SLA — StratoNode"),
    "B1":      (DATASET_DIR/"contracts"/"B1.txt",       "CSA Cover Page — Harbor Retail"),
    "B2":      (DATASET_DIR/"contracts"/"B2.txt",       "Data Processing & Security Addendum — Harbor Retail"),
    "C1":      (DATASET_DIR/"contracts"/"C1.txt",       "CSA Cover Page — Vantage Logistics Corp."),
    "D1":      (DATASET_DIR/"contracts"/"D1.txt",       "Independent Contractor Agreement — Pixelwright"),
}

all_doc_texts = {}
for doc_key, (path, title) in txt_files.items():
    if path.exists():
        content = path.read_text(encoding="utf-8", errors="replace")
        all_doc_texts[doc_key] = (title, content)
        upsert_document(doc_key, title, content, str(path))
        upsert_rag_chunks(doc_key, content)
    else:
        print(f"  [WARN] Missing: {path}")
conn.commit()

# ── PHASE 2: PDF binary uploads ───────────────────────────────────────────────
print()
print("=" * 60)
print("PHASE 2: Ingesting PDF files into document_uploads")
print("=" * 60)

pdf_map = {
    "A1": DATASET_DIR/"contracts"/"A1.pdf",
    "A2": DATASET_DIR/"contracts"/"A2.pdf",
    "A3": DATASET_DIR/"contracts"/"A3.pdf",
    "B1": DATASET_DIR/"contracts"/"B1.pdf",
    "B2": DATASET_DIR/"contracts"/"B2.pdf",
    "C1": DATASET_DIR/"contracts"/"C1.pdf",
    "D1": DATASET_DIR/"contracts"/"D1.pdf",
    "STD": DATASET_DIR/"contracts"/"STD.pdf",
    "Odin_PS": ODIN_PS_PDF,
}

for doc_key, pdf_path in pdf_map.items():
    if not pdf_path.exists():
        print(f"  [WARN] Missing PDF: {pdf_path}")
        continue
    raw_bytes = pdf_path.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    filename = pdf_path.name
    if conn.execute("SELECT document_id FROM document_uploads WHERE owner_id=? AND raw_sha256=?", (DEMO_ORG_ID, raw_sha)).fetchone():
        print(f"  [pdf] SKIP (already uploaded): {filename}")
        continue
    existing_doc = conn.execute("SELECT id FROM documents WHERE owner_id=? AND document_key=?", (DEMO_ORG_ID, doc_key)).fetchone()
    if existing_doc:
        doc_id = existing_doc[0]
    else:
        doc_id = str(uuid.uuid4())
        t = now_iso()
        conn.execute(
            "INSERT INTO documents(id,owner_id,document_key,title,content,content_sha256,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (doc_id, DEMO_ORG_ID, doc_key, filename, "[PDF binary]", raw_sha, str(pdf_path), t, t)
        )
    conn.execute(
        "INSERT OR IGNORE INTO document_uploads(document_id,owner_id,filename,media_type,raw_sha256,raw,page_count,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (doc_id, DEMO_ORG_ID, filename, "application/pdf", raw_sha, raw_bytes, 1, now_iso())
    )
    print(f"  [pdf] Saved PDF binary: {filename} ({len(raw_bytes)} bytes)")
conn.commit()

# Try to extract Odin_PS.pdf text for chunking
print()
print("  Attempting to extract text from Odin_PS.pdf...")
odin_text = None
try:
    import fitz
    doc = fitz.open(str(ODIN_PS_PDF))
    odin_text = "\n\n".join(p.get_text() for p in doc)
    doc.close()
    print(f"  [pdf] Extracted {len(odin_text)} chars via PyMuPDF")
except ImportError:
    try:
        from pdfminer.high_level import extract_text as pdfextract
        odin_text = pdfextract(str(ODIN_PS_PDF))
        print(f"  [pdf] Extracted {len(odin_text)} chars via pdfminer")
    except Exception as ex:
        print(f"  [warn] Could not extract text: {ex}")

if odin_text and len(odin_text.strip()) > 100:
    title = "ODIN Product Specification & Architecture"
    upsert_document("Odin_PS", title, odin_text, str(ODIN_PS_PDF))
    upsert_rag_chunks("Odin_PS", odin_text)
    all_doc_texts["Odin_PS"] = (title, odin_text)
    conn.commit()

# ── PHASE 3: JSONL events ─────────────────────────────────────────────────────
print()
print("=" * 60)
print("PHASE 3: Ingesting JSONL event logs")
print("=" * 60)

all_events = []
event_text_parts = []

for jpath in [DATASET_DIR/"events"/"events_drop1.jsonl", DATASET_DIR/"events"/"events_drop2.jsonl"]:
    if not jpath.exists():
        print(f"  [WARN] Missing: {jpath}")
        continue
    ins = skip = err = 0
    for i, line in enumerate(jpath.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            if upsert_event(ev, str(jpath)):
                ins += 1
                all_events.append(ev)
                event_text_parts.append(
                    f"[{ev.get('event_id','?')}] {ev.get('timestamp','')} | {ev.get('channel','')} | "
                    f"FROM: {ev.get('from','')} | TO: {ev.get('to','')} | SUBJECT: {ev.get('subject','')}\n{ev.get('body','')[:400]}"
                )
            else:
                skip += 1
        except json.JSONDecodeError:
            err += 1
            conn.execute(
                "INSERT OR IGNORE INTO event_import_errors(id,owner_id,source_file,line_number,line_sha256,error_type,recorded_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), DEMO_ORG_ID, str(jpath), i, sha256h(line), "JSON_PARSE_ERROR", now_iso())
            )
    conn.commit()
    print(f"  {jpath.name}: {ins} inserted, {skip} skipped, {err} parse errors")

if event_text_parts:
    events_content = "\n\n---\n\n".join(event_text_parts)
    upsert_document("events_log", "Operational Events & Communications Log (E-01 to E-18)", events_content, "events/*.jsonl")
    upsert_rag_chunks("events_log", events_content)
    conn.commit()

# ── PHASE 4: CSV files ────────────────────────────────────────────────────────
print()
print("=" * 60)
print("PHASE 4: Ingesting CSV data files")
print("=" * 60)

for doc_key, (csv_path, title) in {
    "payments_ledger": (DATASET_DIR/"data"/"payments_ledger.csv", "Quillhub AP/AR Payment Ledger"),
    "holidays":        (DATASET_DIR/"data"/"holidays.csv",         "Business Holidays 2026-2027"),
}.items():
    if not csv_path.exists():
        print(f"  [WARN] Missing CSV: {csv_path}")
        continue
    content = csv_path.read_text(encoding="utf-8", errors="replace")
    upsert_document(doc_key, title, content, str(csv_path))
    upsert_rag_chunks(doc_key, content)
    all_doc_texts[doc_key] = (title, content)
    print(f"  [csv] Saved: {csv_path.name} ({len(content)} chars)")
conn.commit()

# ── PHASE 5: LLM report ───────────────────────────────────────────────────────
print()
print("=" * 60)
print("PHASE 5: Building LLM context & generating report")
print("=" * 60)

MAX_PER_DOC = 3000
context_parts = []
for doc_key, (title, content) in all_doc_texts.items():
    excerpt = content[:MAX_PER_DOC] + ("\n[... truncated ...]" if len(content) > MAX_PER_DOC else "")
    context_parts.append(f"### {title} ({doc_key})\n{excerpt}")

events_summary = "\n".join(
    f"- [{e.get('event_id','?')}] {e.get('timestamp','')} | {e.get('channel','')} | "
    f"{e.get('subject','')} (from {e.get('from','?')} to {e.get('to','?')})"
    for e in all_events
)

system_prompt = (
    "You are ODIN, an AI-powered Financial & Contract Intelligence Engine for Quillhub Inc. "
    "You have full access to the company's contracts, SLAs, operational event logs, payment ledger, "
    "and company context. Generate a comprehensive executive briefing report covering:\n"
    "1. CONTRACT PORTFOLIO OVERVIEW - summarize all active contracts (parties, value, key dates, status)\n"
    "2. SLA COMPLIANCE ANALYSIS - identify any SLA breaches, missed targets, or at-risk commitments\n"
    "3. FINANCIAL EXPOSURE - calculate credits owed, pending invoices, payment status\n"
    "4. OPERATIONAL RISK FLAGS - insurance expiry, vendor non-performance, key deadlines\n"
    "5. CRITICAL FINDINGS - top 5 most urgent items requiring immediate action\n"
    "6. RECOMMENDED NEXT STEPS - concrete actions for the legal and finance teams\n"
    "Format the report professionally with clear sections, bullet points, and risk levels (HIGH/MEDIUM/LOW)."
)

user_prompt = (
    f"Here is the complete dataset for Quillhub Inc. as of today ({datetime.now().strftime('%B %d, %Y')}):\n\n"
    + "\n\n".join(context_parts[:9])
    + "\n\n--- OPERATIONAL EVENTS LOG ---\n"
    + events_summary
    + "\n\nPlease generate the full ODIN Executive Intelligence Report."
)

print(f"  Calling {MODEL} via OpenRouter...")
llm_report = ""
llm_error = None
try:
    resp = requests.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ragnarok.local",
            "X-Title": "ODIN Intelligence Report",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 4000,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    llm_report = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {})
    print(f"  LLM response received! ({len(llm_report)} chars, tokens: {tokens})")
except Exception as e:
    llm_error = str(e)
    print(f"  LLM call failed: {e}")
    llm_report = f"""# ODIN Executive Intelligence Report
Generated: {datetime.now().strftime('%B %d, %Y')} (LLM fallback - call failed: {e})

## 1. CONTRACT PORTFOLIO OVERVIEW
- **StratoNode (A1/A2/A3)**: Cloud hosting agreement. StratoNode provides CloudCore compute/network/storage.
- **Harbor Retail (B1/B2)**: CSA for Route Optimizer. $40,000/month. SLA target 99.9% uptime.
- **Vantage Logistics (C1)**: CSA for Route Optimizer Pro. $18,500/month. Go-live May 15, 2027.
- **Pixelwright (D1)**: Independent contractor for front-end development. Milestone-based payments.

## 2. SLA COMPLIANCE ANALYSIS
- **BREACH (HIGH)**: March 2027 — 99.57% uptime < 99.9% Harbor target (190 min downtime, March 3)
- **BREACH (HIGH)**: May 2027 — 98.87% uptime < 99.9% Harbor target (505 min downtime, May 1-2)
- Harbor SLA was also missed for Vantage in May (first month of service)

## 3. FINANCIAL EXPOSURE
- Harbor Retail credit request: **$12,000** (March + May 2027 SLA credits)
- Pending invoice to Harbor: QH-INV-2027-04-HR for $40,000 (due May 17, 2027)
- Vantage setup fee invoice: QH-INV-2027-SETUP-VL for $12,000 (due July 31, 2027)

## 4. OPERATIONAL RISK FLAGS
- **HIGH**: Insurance policies (MML-2024-88714, MML-2024-88715) expire June 30, 2027. No renewal confirmed.
- **HIGH**: Two SLA breaches triggered Harbor's right to terminate (Section 8.1 if third miss in June 2027)
- **MEDIUM**: Pixelwright M4 delivered late (April 20 vs Feb 28). No formal extension signed.
- **MEDIUM**: Vantage Logistics considering non-renewal (email E-08)

## 5. CRITICAL FINDINGS
1. **[HIGH]** Insurance renewal deadline is June 20, 2027 — immediate action required
2. **[HIGH]** Harbor credit of $12,000 must be processed immediately to avoid dispute escalation
3. **[HIGH]** Third SLA miss in June 2027 would give Harbor termination rights — monitor closely
4. **[MEDIUM]** Vantage non-renewal risk — engage account management team
5. **[MEDIUM]** Pixelwright late delivery — formalize timeline and payment adjustment

## 6. RECOMMENDED NEXT STEPS
- Contact Sarah Mitchell (Meridian Mutual) by June 20 to renew insurance policies
- Apply $12,000 credit to Harbor's next invoice and confirm in writing
- Implement enhanced monitoring for CloudCore uptime in June 2027
- Schedule retention call with Derek Sung (Vantage Logistics)
- Execute written amendment with Pixelwright for M4 timeline extension
"""

# Save report to DB
report_id = str(uuid.uuid4())
conn.execute(
    "INSERT INTO web_records(id,owner_id,kind,data,created_at,updated_at) VALUES(?,?,?,?,?,?)",
    (report_id, DEMO_ORG_ID, "llm_report",
     json.dumps({"report": llm_report, "generated_at": now_iso(), "model": MODEL}),
     now_iso(), now_iso())
)
conn.commit()
print(f"  [db] LLM report saved: {report_id}")

# ── PHASE 6: Send email via Resend ────────────────────────────────────────────
print()
print("=" * 60)
print("PHASE 6: Sending email report via Resend")
print("=" * 60)

total_docs   = conn.execute("SELECT COUNT(*) FROM documents WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
total_chunks = conn.execute("SELECT COUNT(*) FROM rag_chunks WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
total_events = conn.execute("SELECT COUNT(*) FROM operational_events WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]

def md_to_html(text):
    lines = text.split("\n")
    out = []
    in_ul = False
    for line in lines:
        if line.startswith("# "):
            if in_ul: out.append("</ul>"); in_ul=False
            out.append(f"<h1 style='color:#fff;font-size:20px;margin:24px 0 12px'>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_ul: out.append("</ul>"); in_ul=False
            out.append(f"<h2 style='color:#e2a000;font-size:16px;margin:20px 0 8px;border-bottom:1px solid #333;padding-bottom:6px'>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_ul: out.append("</ul>"); in_ul=False
            out.append(f"<h3 style='color:#bbb;font-size:14px;margin:14px 0 6px'>{line[4:]}</h3>")
        elif line.startswith(("- ", "* ")):
            if not in_ul: out.append("<ul style='margin:8px 0 8px 20px;padding:0'>"); in_ul=True
            c = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line[2:])
            c = c.replace("**HIGH**","<b style='color:#f44'>HIGH</b>").replace("**MEDIUM**","<b style='color:#fa0'>MEDIUM</b>").replace("**LOW**","<b style='color:#4c4'>LOW</b>")
            out.append(f"<li style='margin:4px 0'>{c}</li>")
        elif line.strip() == "---":
            if in_ul: out.append("</ul>"); in_ul=False
            out.append("<hr style='border:none;border-top:1px solid #333;margin:16px 0'>")
        elif line.strip():
            if in_ul: out.append("</ul>"); in_ul=False
            c = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            out.append(f"<p style='margin:6px 0;color:#ccc'>{c}</p>")
    if in_ul: out.append("</ul>")
    return "\n".join(out)

body_html = md_to_html(llm_report)
gen_time = datetime.now().strftime("%B %d, %Y at %H:%M UTC")

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Arial,sans-serif;color:#e0e0e0">
<div style="max-width:800px;margin:0 auto">
  <div style="background:linear-gradient(135deg,#1a0a2e,#0d0d1a,#0a1628);padding:40px;border-bottom:3px solid #e2a000">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td><div style="display:inline-block;width:48px;height:48px;background:#e2a000;border-radius:8px;text-align:center;line-height:48px;font-size:22px">⚡</div></td>
      <td style="padding-left:16px"><div style="font-size:28px;font-weight:900;color:#e2a000;letter-spacing:3px">ODIN</div>
      <div style="font-size:11px;color:#888;letter-spacing:1px">FINANCIAL &amp; CONTRACT INTELLIGENCE ENGINE</div></td>
    </tr></table>
    <h1 style="color:#fff;font-size:22px;margin:20px 0 8px">Executive Intelligence Report</h1>
    <p style="color:#aaa;font-size:13px;margin:0">Generated: {gen_time} &nbsp;|&nbsp; Model: {MODEL}</p>
  </div>
  <div style="background:#111118;padding:20px 40px;border-bottom:1px solid #222">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="text-align:center"><div style="font-size:32px;font-weight:900;color:#e2a000">{total_docs}</div><div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">Documents</div></td>
      <td style="text-align:center"><div style="font-size:32px;font-weight:900;color:#e2a000">{total_chunks}</div><div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">RAG Chunks</div></td>
      <td style="text-align:center"><div style="font-size:32px;font-weight:900;color:#e2a000">{total_events}</div><div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">Events Indexed</div></td>
      <td style="text-align:center"><div style="font-size:32px;font-weight:900;color:#4caf50">✓</div><div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">DB Status</div></td>
    </tr></table>
  </div>
  <div style="background:#0f0f1a;padding:40px;line-height:1.8;font-size:14px">
    {body_html}
  </div>
  <div style="background:#111118;padding:24px 40px;border-top:1px solid #222">
    <h3 style="color:#e2a000;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px">Dataset Ingested</h3>
    <table width="100%" style="font-size:12px;color:#999;border-collapse:collapse">
      <tr style="border-bottom:1px solid #222"><th style="text-align:left;padding:4px 0;color:#666">File</th><th style="text-align:left;padding:4px 0;color:#666">Type</th><th style="text-align:left;padding:4px 0;color:#666">Description</th></tr>
      <tr><td>context.txt</td><td style="color:#e2a000">TXT</td><td>Quillhub Company Context</td></tr>
      <tr><td>STD.txt/pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Standard Terms v2.0</td></tr>
      <tr><td>A1-A3 .txt/.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>StratoNode Contracts &amp; SLA</td></tr>
      <tr><td>B1-B2 .txt/.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Harbor Retail Agreements</td></tr>
      <tr><td>C1 .txt/.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Vantage Logistics Agreement</td></tr>
      <tr><td>D1 .txt/.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Pixelwright Contractor Agreement</td></tr>
      <tr><td>Odin_PS.pdf</td><td style="color:#e2a000">PDF</td><td>ODIN Product Specification</td></tr>
      <tr><td>events_drop1.jsonl</td><td style="color:#4caf50">JSONL</td><td>Events E-01 to E-10</td></tr>
      <tr><td>events_drop2.jsonl</td><td style="color:#4caf50">JSONL</td><td>Events E-11 to E-18</td></tr>
      <tr><td>payments_ledger.csv</td><td style="color:#2196f3">CSV</td><td>AP/AR Payment Ledger</td></tr>
      <tr><td>holidays.csv</td><td style="color:#2196f3">CSV</td><td>Holiday Calendar 2026-2027</td></tr>
    </table>
  </div>
  <div style="background:#0a0a0f;padding:24px 40px;border-top:3px solid #e2a000;text-align:center">
    <p style="color:#555;font-size:11px;margin:0">ODIN Intelligence Engine | Ragnarok Demo | Sent to {EMAIL_TO}</p>
    <p style="color:#333;font-size:10px;margin:6px 0 0">Auto-generated by ODIN using {MODEL} via OpenRouter</p>
  </div>
</div></body></html>"""

plain_text = f"ODIN Executive Intelligence Report\nGenerated: {gen_time}\nModel: {MODEL}\n\nDocuments: {total_docs} | RAG Chunks: {total_chunks} | Events: {total_events}\n\n{llm_report}"

print(f"  Sending email to {EMAIL_TO}...")
try:
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={
            "from": f"ODIN Intelligence Engine <{RESEND_FROM}>",
            "to":   [EMAIL_TO],
            "subject": f"ODIN Executive Intelligence Report — {datetime.now().strftime('%B %d, %Y')}",
            "html": html,
            "text": plain_text,
        },
        timeout=30,
    )
    r.raise_for_status()
    eid = r.json().get("id", "unknown")
    print(f"  Email sent! Resend ID: {eid}")
    conn.execute(
        "INSERT INTO web_records(id,owner_id,kind,data,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (str(uuid.uuid4()), DEMO_ORG_ID, "email_sent",
         json.dumps({"resend_id": eid, "to": EMAIL_TO, "sent_at": now_iso()}),
         now_iso(), now_iso())
    )
    conn.commit()
except Exception as e:
    print(f"  Email failed: {e}")
    if hasattr(e, "response") and e.response is not None:
        print(f"     {e.response.text}")

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("INGESTION COMPLETE")
print("=" * 60)
td = conn.execute("SELECT COUNT(*) FROM documents WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
tc = conn.execute("SELECT COUNT(*) FROM rag_chunks WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
te = conn.execute("SELECT COUNT(*) FROM operational_events WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
tu = conn.execute("SELECT COUNT(*) FROM document_uploads WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
wr = conn.execute("SELECT COUNT(*) FROM web_records WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
print(f"  Org: Ragnarok Demo | Login: demo@ragnarok.local")
print(f"  Documents:          {td}")
print(f"  RAG Chunks:         {tc}")
print(f"  Operational Events: {te}")
print(f"  PDF Uploads:        {tu}")
print(f"  Web Records:        {wr}")
print(f"  LLM: {'OK' if not llm_error else 'FAILED: ' + llm_error}")
print(f"  Email: {EMAIL_TO}")
print()
print("Demo account is READY for login!")
conn.close()
