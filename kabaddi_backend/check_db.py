import sqlite3
import os

db_path = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend\db.sqlite3"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT status, error_message FROM api_usersession ORDER BY created_at DESC LIMIT 1")
row = cur.fetchone()
if row:
    print(f"STATUS: {row[0]}")
    print(f"ERROR: {row[1]}")
else:
    print("No sessions found.")
conn.close()
