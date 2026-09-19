# Adversarial Case: E5_1 - Feature pop before inference
# Intended Mechanism: Feature popped from metadata dictionary
meta = {'feature_cols': ['f1', 'f2', 'f3', 'f4', 'f5']}
meta['feature_cols'].pop(0) # Drops feature at runtime
