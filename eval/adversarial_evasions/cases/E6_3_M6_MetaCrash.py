# Adversarial Case: E6_3 - Missing schema dictionary key
# Intended Mechanism: Key deleted from metadata dict; default getter returns malformed list
meta = {'state_beds': {'MH': 1000}}
# feature_cols completely missing
features = meta.get('feature_cols', [])
if len(features) == 0: raise KeyError("Corrupted metadata")
