"""Copy operational_events and memories from local-owner to org."""
import sqlite3, uuid
from datetime import datetime, timezone

DB_PATH = 'data/ragnarok.sqlite3'
LOCAL_OWNER = 'local-owner'
ORG_ID = '149b8919-d90c-4007-bf0f-1b8d33414ac6'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Check unique constraint on operational_events
info = conn.execute("SELECT sql FROM sqlite_master WHERE name='operational_events'").fetchone()
print("Table DDL:", info['sql'][:200] if info else 'not found')

events = conn.execute("SELECT * FROM operational_events WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"\nCopying {len(events)} operational_events...")
copied = 0
for e in events:
    existing = conn.execute("SELECT event_id FROM operational_events WHERE owner_id=? AND event_id=?", (ORG_ID, e['event_id'])).fetchone()
    if not existing:
        try:
            conn.execute(
                "INSERT INTO operational_events(id, owner_id, event_id, occurred_at, channel, sender, recipient, subject, body, content_sha256, source, imported_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), ORG_ID, e['event_id'], e['occurred_at'], e['channel'], e['sender'], e['recipient'], e['subject'], e['body'], e['content_sha256'], e['source'], e['imported_at'])
            )
            copied += 1
        except Exception as ex:
            print(f"  ERROR {e['event_id']}: {ex}")

# Also copy memories
memories = conn.execute("SELECT * FROM memories WHERE owner_id=?", (LOCAL_OWNER,)).fetchall()
print(f"\nCopying {len(memories)} memories...")
mem_copied = 0
for m in memories:
    existing = conn.execute("SELECT id FROM memories WHERE owner_id=? AND content=?", (ORG_ID, m['content'])).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO memories(id, owner_id, kind, content, source, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), ORG_ID, m['kind'], m['content'], m['source'], m['created_at'], m['updated_at'])
        )
        mem_copied += 1

conn.commit()
conn.close()
print(f"\nDone: {copied} events, {mem_copied} memories copied to org {ORG_ID}")
