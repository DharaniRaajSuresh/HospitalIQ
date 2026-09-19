# Adversarial Case: E7_1 - Broad exception return constant array
# Intended Mechanism: Broad try-except returning hardcoded constant 450
def predict_beds(state):
    try:
        return model.predict(state)
    except Exception:
        return [450, 450, 450] # Hardcoded constant fallback
