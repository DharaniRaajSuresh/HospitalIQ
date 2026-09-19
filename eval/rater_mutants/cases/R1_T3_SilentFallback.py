# Rater 1 - Tier 3: Deployment: Try-except returning hardcoded zeros array
# Style: Broad except handler
def get_prediction(X):
    try:
        return model.predict(X)
    except Exception:
        return [0, 0, 0]
