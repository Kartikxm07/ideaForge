"""Send the LLM report email via Resend - using sandbox-compatible recipient."""
import os, json, sqlite3, requests, re
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent

def load_env():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM    = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
MODEL          = os.environ.get("MODEL_HEAVY", "openai/gpt-oss-120b")
DEMO_ORG_ID    = "48bb8512-ace0-4ee5-a8a6-6965bac7939a"

# Resend sandbox mode: can ONLY send to the verified account owner email
# The Resend account belongs to: shuklaatharv2005@gmail.com
EMAIL_TO       = "shuklaatharv2005@gmail.com"
INTENDED_FOR   = "atharvmanojshukla7@gmail.com"

DB_PATH = BASE_DIR / "data" / "ragnarok.sqlite3"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

# Fetch the latest LLM report
row = conn.execute(
    "SELECT data FROM web_records WHERE owner_id=? AND kind=? ORDER BY created_at DESC LIMIT 1",
    (DEMO_ORG_ID, "llm_report")
).fetchone()

report_data = json.loads(row["data"])
llm_report = report_data.get("report", "No report found")
total_docs   = conn.execute("SELECT COUNT(*) FROM documents WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
total_chunks = conn.execute("SELECT COUNT(*) FROM rag_chunks WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]
total_events = conn.execute("SELECT COUNT(*) FROM operational_events WHERE owner_id=?", (DEMO_ORG_ID,)).fetchone()[0]

print(f"LLM report: {len(llm_report)} chars")
print(f"DB stats: {total_docs} docs, {total_chunks} chunks, {total_events} events")

def md_to_html(text):
    lines = text.split("\n")
    out = []
    in_ul = False
    for line in lines:
        if line.startswith("# "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h1 style='color:#fff;font-size:20px;margin:24px 0 12px'>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h2 style='color:#e2a000;font-size:16px;margin:20px 0 8px;border-bottom:1px solid #333;padding-bottom:6px'>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h3 style='color:#bbb;font-size:14px;margin:14px 0 6px'>{line[4:]}</h3>")
        elif line.startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul style='margin:8px 0 8px 20px;padding:0'>")
                in_ul = True
            c = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line[2:])
            out.append(f"<li style='margin:4px 0;color:#ccc'>{c}</li>")
        elif line.strip() == "---":
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append("<hr style='border:none;border-top:1px solid #333;margin:16px 0'>")
        elif line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            c = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            out.append(f"<p style='margin:6px 0;color:#ccc'>{c}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)

body_html = md_to_html(llm_report)
gen_time = datetime.now().strftime("%B %d, %Y at %H:%M UTC")

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Arial,sans-serif;color:#e0e0e0">
<div style="max-width:800px;margin:0 auto">

  <div style="background:linear-gradient(135deg,#1a0a2e,#0d0d1a,#0a1628);padding:40px;border-bottom:3px solid #e2a000">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td width="64"><div style="width:48px;height:48px;background:#e2a000;border-radius:8px;text-align:center;line-height:48px;font-size:22px">⚡</div></td>
      <td style="padding-left:16px">
        <div style="font-size:28px;font-weight:900;color:#e2a000;letter-spacing:3px">ODIN</div>
        <div style="font-size:11px;color:#888;letter-spacing:1px">FINANCIAL &amp; CONTRACT INTELLIGENCE ENGINE</div>
      </td>
    </tr></table>
    <h1 style="color:#fff;font-size:22px;margin:20px 0 8px">Executive Intelligence Report</h1>
    <p style="color:#aaa;font-size:13px;margin:0">Generated: {gen_time} &nbsp;|&nbsp; Model: {MODEL}</p>
    <div style="margin-top:12px;padding:10px 16px;background:#1a1400;border:1px solid #e2a000;border-radius:6px;font-size:12px;color:#e2a000">
      📧 Intended for: <strong>{INTENDED_FOR}</strong> — delivered to sandbox-verified address per Resend free-tier policy.<br>
      To send directly, verify a domain at <a href="https://resend.com/domains" style="color:#e2a000">resend.com/domains</a>.
    </div>
  </div>

  <div style="background:#111118;padding:20px 40px;border-bottom:1px solid #222">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="text-align:center">
        <div style="font-size:32px;font-weight:900;color:#e2a000">{total_docs}</div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">Documents</div>
      </td>
      <td style="text-align:center">
        <div style="font-size:32px;font-weight:900;color:#e2a000">{total_chunks}</div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">RAG Chunks</div>
      </td>
      <td style="text-align:center">
        <div style="font-size:32px;font-weight:900;color:#e2a000">{total_events}</div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">Events Indexed</div>
      </td>
      <td style="text-align:center">
        <div style="font-size:32px;font-weight:900;color:#4caf50">&#10003;</div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px">DB Status</div>
      </td>
    </tr></table>
  </div>

  <div style="background:#0f0f1a;padding:40px;line-height:1.8;font-size:14px">
    {body_html}
  </div>

  <div style="background:#111118;padding:24px 40px;border-top:1px solid #222">
    <h3 style="color:#e2a000;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px">Dataset Ingested into DB</h3>
    <table width="100%" style="font-size:12px;color:#999;border-collapse:collapse">
      <tr style="border-bottom:1px solid #222">
        <th style="text-align:left;padding:4px 8px 4px 0;color:#666">File</th>
        <th style="text-align:left;padding:4px 0;color:#666">Type</th>
        <th style="text-align:left;padding:4px 0;color:#666">Description</th>
      </tr>
      <tr><td style="padding:3px 8px 3px 0">context.txt</td><td style="color:#e2a000">TXT</td><td>Quillhub Company Context</td></tr>
      <tr><td style="padding:3px 8px 3px 0">STD.txt / STD.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Standard CSA Terms v2.0 (38 chunks)</td></tr>
      <tr><td style="padding:3px 8px 3px 0">A1.txt / A1.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>StratoNode Cover Page</td></tr>
      <tr><td style="padding:3px 8px 3px 0">A2.txt / A2.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>StratoNode CloudCore SLA</td></tr>
      <tr><td style="padding:3px 8px 3px 0">A3.txt / A3.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>SLA Amendment No.1</td></tr>
      <tr><td style="padding:3px 8px 3px 0">B1.txt / B1.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Harbor Retail Cover Page</td></tr>
      <tr><td style="padding:3px 8px 3px 0">B2.txt / B2.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Harbor Data Processing Addendum</td></tr>
      <tr><td style="padding:3px 8px 3px 0">C1.txt / C1.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Vantage Logistics Agreement</td></tr>
      <tr><td style="padding:3px 8px 3px 0">D1.txt / D1.pdf</td><td style="color:#e2a000">TXT+PDF</td><td>Pixelwright Contractor Agreement</td></tr>
      <tr><td style="padding:3px 8px 3px 0">Odin_PS.pdf</td><td style="color:#e2a000">PDF</td><td>ODIN Product Specification (PyMuPDF extracted)</td></tr>
      <tr><td style="padding:3px 8px 3px 0">events_drop1.jsonl</td><td style="color:#4caf50">JSONL</td><td>Events E-01 to E-10</td></tr>
      <tr><td style="padding:3px 8px 3px 0">events_drop2.jsonl</td><td style="color:#4caf50">JSONL</td><td>Events E-11 to E-18</td></tr>
      <tr><td style="padding:3px 8px 3px 0">payments_ledger.csv</td><td style="color:#2196f3">CSV</td><td>AP/AR Payment Ledger</td></tr>
      <tr><td style="padding:3px 8px 3px 0">holidays.csv</td><td style="color:#2196f3">CSV</td><td>Holiday Calendar 2026-2027</td></tr>
    </table>
  </div>

  <div style="background:#0a0a0f;padding:24px 40px;border-top:3px solid #e2a000;text-align:center">
    <p style="color:#555;font-size:11px;margin:0">
      ODIN Intelligence Engine &nbsp;|&nbsp; Ragnarok Demo &nbsp;|&nbsp;
      Intended for: {INTENDED_FOR}
    </p>
    <p style="color:#333;font-size:10px;margin:6px 0 0">
      Auto-generated by ODIN using {MODEL} via OpenRouter. All data stored in local SQLite for demo.
    </p>
  </div>

</div>
</body></html>"""

plain_text = (
    f"ODIN Executive Intelligence Report\n"
    f"Generated: {gen_time} | Model: {MODEL}\n"
    f"Intended for: {INTENDED_FOR}\n\n"
    f"Documents: {total_docs} | RAG Chunks: {total_chunks} | Events: {total_events}\n\n"
    f"{llm_report}"
)

print(f"\nSending email to {EMAIL_TO} (intended for {INTENDED_FOR})...")
try:
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": f"ODIN Intelligence Engine <{RESEND_FROM}>",
            "to":   [EMAIL_TO],
            "subject": f"[ODIN] Executive Intelligence Report — {datetime.now().strftime('%B %d, %Y')} (for {INTENDED_FOR})",
            "html": html,
            "text": plain_text,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    email_id = data.get("id", "unknown")
    print(f"SUCCESS! Email sent via Resend — ID: {email_id}")
    print(f"Check inbox: {EMAIL_TO}")
    print(f"(Intended for: {INTENDED_FOR})")
    
    # Log to DB
    import uuid
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO web_records(id,owner_id,kind,data,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (str(uuid.uuid4()), DEMO_ORG_ID, "email_sent",
         json.dumps({"resend_id": email_id, "to": EMAIL_TO, "intended_for": INTENDED_FOR, "sent_at": now}),
         now, now)
    )
    conn.commit()
except Exception as e:
    print(f"FAILED: {e}")
    if hasattr(e, "response") and e.response is not None:
        print(f"Response: {e.response.text}")

conn.close()
