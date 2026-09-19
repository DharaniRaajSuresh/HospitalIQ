# Rater 2 - Tier 3: Deployment: Feature list mutated via dictionary pop
# Style: OOP model container
class ModelArtifact:
    def __init__(self, metadata):
        self.meta = metadata
        self.meta['feature_names'].pop(0)
