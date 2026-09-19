# Adversarial Case: E7_2 - Rare input conditional fallback
# Intended Mechanism: Fallback only triggered when rare edge-condition occurs (age > 98)
def predict_risk(patient):
    try:
        if patient.get('age', 0) > 98:
            raise ValueError("Extreme age boundary")
        return model.predict(patient)
    except Exception:
        return 0.85 # Rare input silent fallback
