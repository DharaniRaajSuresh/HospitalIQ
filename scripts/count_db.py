import sqlite3
conn = sqlite3.connect(r'C:\hospi\ml_pipeline\data\hospitaliq.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in c.fetchall()]
total = 0
for tbl in tables:
    c.execute(f'SELECT COUNT(*) FROM {tbl}')
    count = c.fetchone()[0]
    print(f'{tbl}: {count:,}')
    total += count
print(f'\nTotal Records: {total:,}')
