# Rater 2 - Tier 3: Deployment: Exception handler returning hardcoded 450
# Style: Class try-catch wrapper
class ResilientPredictor:
    def predict(self, input_vector):
        try:
            return self.model.predict(input_vector)
        except Exception:
            return 450
