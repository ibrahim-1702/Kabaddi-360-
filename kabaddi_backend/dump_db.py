import sqlite3
import os

db_path = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend\db.sqlite3"
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, status, error_message FROM api_usersession ORDER BY created_at DESC LIMIT 10")
    rows = cur.fetchall()
    
    with open("db_dump.txt", "w") as f:
        for r in rows:
            f.write(f"ID: {r[0]} | STAT: {r[1]} | ERR: {r[2]}\n")
    conn.close()
    print("Done")
except Exception as e:
    with open("db_dump.txt", "w") as f:
        f.write(str(e))
