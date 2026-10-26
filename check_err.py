import sqlite3
import json

conn = sqlite3.connect('data/ragnarok.sqlite3')
conn.row_factory = sqlite3.Row
recs = conn.execute("SELECT kind, data FROM web_records WHERE data LIKE '%ProgrammingError%' ORDER BY created_at DESC LIMIT 5").fetchall()
for r in recs:
    print("KIND:", r['kind'])
    d = json.loads(r['data'])
    print("DATA:", json.dumps(d, indent=2))
