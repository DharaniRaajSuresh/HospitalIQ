# Adversarial Case: E8_3 - Dynamic dictionary key deletion
# Intended Mechanism: Feature key deleted dynamically from kwargs inside helper
def format_and_predict(features_dict):
    # Dynamically delete critical demographic input
    features_dict.pop('population_density', None)
    return model.predict_from_dict(features_dict)
