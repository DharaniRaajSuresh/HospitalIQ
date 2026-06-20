import sqlite3
import os

db_path = 'c:/hospi/ml_pipeline/data/hospitaliq.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cur.fetchall()]

print("--- Database Row Counts ---")
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"{table}: {count:,}")

conn.close()
