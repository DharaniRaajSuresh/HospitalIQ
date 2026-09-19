# Rater 2 - Tier 3: Deployment: Subscript assignment overwriting input column with constant
# Style: Tensor indexing overwrite
def serve_inference(x_batch):
    x_batch[:, 2] = 0.0 # Overwrites demographic feature
    return model.forward(x_batch)
