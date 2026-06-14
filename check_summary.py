import sqlite3, time
conn = sqlite3.connect('ml_pipeline/data/hospitaliq.db')
rows = conn.execute('SELECT state, total_beds, avg_success_rate, avg_death_rate, updated_at FROM state_summaries ORDER BY state').fetchall()
print(f'Rows in state_summaries: {len(rows)}')
for r in rows[:6]:
    label = r[0] if r[0] else 'All India'
    print(f'  {label} | beds={r[1]} | success={r[2]}% | death_rate={r[3]}')

# Now benchmark the API call speed via direct DB query
print('\n=== SPEED BENCHMARK (direct DB) ===')
t = time.time()
result = conn.execute("SELECT * FROM state_summaries WHERE state = 'Maharashtra'").fetchone()
print(f'Maharashtra lookup: {round((time.time()-t)*1000, 2)}ms  -> found: {result is not None}')

t = time.time()
result = conn.execute("SELECT * FROM state_summaries WHERE state IS NULL").fetchone()
print(f'All India lookup:   {round((time.time()-t)*1000, 2)}ms  -> found: {result is not None}')

conn.close()
