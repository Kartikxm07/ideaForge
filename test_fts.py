import sqlite3
conn = sqlite3.connect('data/ragnarok.sqlite3')
rows = conn.execute("SELECT id, owner_id, document_key, text FROM rag_chunks_fts WHERE rag_chunks_fts MATCH 'StratoNode'").fetchall()
print(f"Matches for StratoNode: {len(rows)}")
for r in rows[:5]:
    print(r[0], r[1], r[2], r[3][:80].replace('\n', ' '))
