# Adversarial Case: E7_4 - Cross-module exception wrapper
# Intended Mechanism: Fallback handler implemented in separate imported decorator middleware
from error_middleware import silent_resilience_wrapper

@silent_resilience_wrapper(default_value=450)
def predict_beds_protected(state):
    return model.predict(state)
