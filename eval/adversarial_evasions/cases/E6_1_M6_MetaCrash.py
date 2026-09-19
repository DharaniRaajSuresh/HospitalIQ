# Adversarial Case: E6_1 - Corrupted pickle payload
# Intended Mechanism: Invalid pickle binary payload raising TypeError on load
# Malformed metadata dictionary serialization
del meta['feature_cols']
