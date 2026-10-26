import sqlite3, json
conn = sqlite3.connect('data/ragnarok.sqlite3')
conn.row_factory = sqlite3.Row

# Schema for web_users
schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='web_users'").fetchone()
print("web_users schema:", schema['sql'] if schema else 'not found')

schema2 = conn.execute("SELECT sql FROM sqlite_master WHERE name='web_orgs'").fetchone()
print("web_orgs schema:", schema2['sql'][:300] if schema2 else 'not found')

users = conn.execute("SELECT * FROM web_users LIMIT 5").fetchall()
print("\nweb_users:")
for u in users:
    d = dict(u)
    d.pop('password_hash', None)
    print(f"  {d}")

orgs = conn.execute("SELECT * FROM web_orgs LIMIT 5").fetchall()
print("\nweb_orgs:")
for o in orgs:
    print(f"  {dict(o)}")

members = conn.execute("SELECT * FROM web_members LIMIT 5").fetchall()
print("\nweb_members:")
for m in members:
    print(f"  {dict(m)}")

conn.close()
