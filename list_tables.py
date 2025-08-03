import sqlite3

conn = sqlite3.connect('instance/plasma.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view');")
tables = cur.fetchall()
for t in tables:
    print(t[0])
conn.close()
