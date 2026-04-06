import sqlite3
try:
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT status, error_message FROM api_usersession ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    print("----- DATABASE STATUS -----")
    print("STATUS:", row[0])
    print("ERROR:", row[1])
except Exception as e:
    print("SCRIPT ERROR:", e)
