import sqlite3, time
conn = sqlite3.connect('ml_pipeline/data/hospitaliq.db')

# Check existing indexes
rows = conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name").fetchall()
print("=== EXISTING INDEXES ===")
for r in rows:
    print(f"  {r[0]} | {r[1]}")
print(f"Total indexes: {len(rows)}")

# Benchmark the slow queries
print("\n=== QUERY BENCHMARKS ===")

queries = [
    ("mortality_records COUNT+AVG+SUM (no filter)", "SELECT COUNT(id), AVG(death_rate), SUM(death_count) FROM mortality_records"),
    ("mortality_records DISTINCT state", "SELECT DISTINCT state FROM mortality_records"),
    ("mortality_records DISTINCT district,state", "SELECT DISTINCT district, state FROM mortality_records ORDER BY district"),
    ("mortality_records GROUP BY district (pop)", "SELECT district, MAX(population) FROM mortality_records GROUP BY district"),
    ("mortality_records GROUP BY cause", "SELECT cause_of_death, SUM(death_count) FROM mortality_records GROUP BY cause_of_death ORDER BY SUM(death_count) DESC LIMIT 5"),
    ("hospital_outcomes AVG success+score", "SELECT COUNT(id), AVG(success_rate), AVG(hospital_score), COUNT(DISTINCT hospital_id) FROM hospital_outcomes"),
    ("hospital_outcomes ORDER BY score DESC LIMIT 1", "SELECT hospital_name, hospital_type, hospital_score, success_rate, district FROM hospital_outcomes ORDER BY hospital_score DESC LIMIT 1"),
    ("hospital_beds GROUP BY hospital_name MAX beds", "SELECT hospital_name, MAX(total_beds) FROM hospital_beds GROUP BY hospital_name"),
    ("hospital_beds AVG occupancy", "SELECT AVG(occupancy_rate) FROM hospital_beds"),
]

for label, sql in queries:
    t = time.time()
    conn.execute(sql).fetchall()
    ms = round((time.time() - t) * 1000)
    print(f"  {ms}ms  {label}")

conn.close()
