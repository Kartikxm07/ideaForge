"""Check database schema to understand existing tables."""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect('data/ragnarok.sqlite3')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('TABLES:', [t[0] for t in tables])
print()
for t in tables:
    tname = t[0]
    cols = conn.execute(f'PRAGMA table_info({tname})').fetchall()
    count = conn.execute(f'SELECT COUNT(*) FROM {tname}').fetchone()[0]
    print(f'  {tname} ({count} rows): {[c[1] for c in cols]}')
conn.close()
