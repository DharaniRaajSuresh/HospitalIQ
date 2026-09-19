# Adversarial Case: E7_3 - Fallback to cached state mean
# Intended Mechanism: Fallback queries precomputed SQLite state average
def predict_mortality(state):
    try:
        return model.predict(state)
    except Exception:
        return db.query("SELECT avg_deaths FROM state_cache WHERE state=?", state)
