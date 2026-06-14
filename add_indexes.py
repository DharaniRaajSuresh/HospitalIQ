import sqlite3, time

conn = sqlite3.connect('ml_pipeline/data/hospitaliq.db')
conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrent reads

print("Creating missing indexes...")

indexes = [
    # mortality_records - missing composite and column indexes
    ("idx_mort_district_state", "CREATE INDEX IF NOT EXISTS idx_mort_district_state ON mortality_records(district, state)"),
    ("idx_mort_cause", "CREATE INDEX IF NOT EXISTS idx_mort_cause ON mortality_records(cause_of_death)"),
    ("idx_mort_district_pop", "CREATE INDEX IF NOT EXISTS idx_mort_district_pop ON mortality_records(district, population)"),
    ("idx_mort_state_district", "CREATE INDEX IF NOT EXISTS idx_mort_state_district ON mortality_records(state, district)"),
    ("idx_mort_death_rate", "CREATE INDEX IF NOT EXISTS idx_mort_death_rate ON mortality_records(death_rate)"),
    ("idx_mort_death_count", "CREATE INDEX IF NOT EXISTS idx_mort_death_count ON mortality_records(death_count)"),
    # hospital_outcomes - missing score and composite indexes
    ("idx_hosp_score", "CREATE INDEX IF NOT EXISTS idx_hosp_score ON hospital_outcomes(hospital_score DESC)"),
    ("idx_hosp_success_rate", "CREATE INDEX IF NOT EXISTS idx_hosp_success_rate ON hospital_outcomes(success_rate DESC)"),
    ("idx_hosp_state_district", "CREATE INDEX IF NOT EXISTS idx_hosp_state_district ON hospital_outcomes(state, district)"),
    ("idx_hosp_type", "CREATE INDEX IF NOT EXISTS idx_hosp_type ON hospital_outcomes(hospital_type)"),
    # hospital_beds - missing composite indexes
    ("idx_beds_state_district", "CREATE INDEX IF NOT EXISTS idx_beds_state_district ON hospital_beds(state, district)"),
    ("idx_beds_hosp_name", "CREATE INDEX IF NOT EXISTS idx_beds_hosp_name ON hospital_beds(hospital_name)"),
    ("idx_beds_occupancy", "CREATE INDEX IF NOT EXISTS idx_beds_occupancy ON hospital_beds(occupancy_rate)"),
]

for name, sql in indexes:
    t = time.time()
    conn.execute(sql)
    conn.commit()
    ms = round((time.time() - t) * 1000)
    print(f"  {ms}ms  {name}")

print("\nAll indexes created! Re-running benchmarks...")
print("=== QUERY BENCHMARKS AFTER INDEXING ===")

queries = [
    ("mortality COUNT+AVG+SUM", "SELECT COUNT(id), AVG(death_rate), SUM(death_count) FROM mortality_records"),
    ("mortality DISTINCT state", "SELECT DISTINCT state FROM mortality_records"),
    ("mortality DISTINCT district,state", "SELECT DISTINCT district, state FROM mortality_records ORDER BY district"),
    ("mortality GROUP BY district (pop)", "SELECT district, MAX(population) FROM mortality_records GROUP BY district"),
    ("mortality GROUP BY cause_of_death", "SELECT cause_of_death, SUM(death_count) FROM mortality_records GROUP BY cause_of_death ORDER BY SUM(death_count) DESC LIMIT 5"),
    ("hospital_outcomes AVG success+score COUNT DISTINCT", "SELECT COUNT(id), AVG(success_rate), AVG(hospital_score), COUNT(DISTINCT hospital_id) FROM hospital_outcomes"),
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
print("\nDone.")
