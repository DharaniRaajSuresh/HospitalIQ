# RATER PROTOCOL: INDEPENDENT TAXONOMY-ONLY MUTANT SPECIFICATION
**Timestamped Materials Provided to Independent Evaluators (Rater 1 & Rater 2)**

- **Eligibility**: Independent evaluation team members who have NOT accessed HospitalIQ source code, training pipelines, or M1–M9 operator scripts.
- **Supplied Information**: Abstract defect definitions only. No sample code, no repository references, and no existing mutants.

---

## Abstract Defect Taxonomy Tiers Provided to Raters

### Tier 1: Data Provenance & Ingestion Breach
*Definition*: A dataset contains records tagged with an authentic origin metadata label, but the records actually originate from an unverified synthetic tail or post-date the verified data collection window.

### Tier 2: Statistical Formulation & Temporal Lineage Breach
*Sub-archetypes*:
1. **Target Invariance / Formula Reconstruction**: The target $y$ is computed as a deterministic mathematical function of the training feature inputs $X$.
2. **Contemporaneous Leakage**: Feature columns incorporate contemporaneous (same-period) aggregate statistics or forward-looking lookaheads of the prediction target.
3. **Temporal Ordering Breach**: Time-series training and testing data are shuffled or randomly partitioned non-chronologically.

### Tier 3: Deployment Interface & Runtime Resilience Breach
*Sub-archetypes*:
1. **Dimension / Signature Drift**: The feature dimensionality expected by the model artifact differs from the dimensionality supplied by the production serving script.
2. **Metadata Corruption**: Serialized model metadata or pipeline contracts contain corrupted keys or invalid type definitions that cause unhandled exceptions upon initialization.
3. **Silent Exception Fallback**: Production inference wraps prediction logic in a broad exception handler that swallows operational errors and returns a hardcoded default value.
4. **Input Feature Omission**: An input feature accepted by the inference API is ignored during model execution and replaced with a static constant.
5. **Unmounted Monitoring Route**: A health, telemetry, or audit route defined in the service is never mounted to the active application router.

---

## Implementation Rules for Raters
1. Author 1 defect instance per sub-archetype in your own preferred programming style (functional, OOP, or script).
2. Do not discuss or coordinate implementations with the other rater.
3. Keep code self-contained and runnable using standard Python / NumPy / Pandas / Scikit-Learn libraries.
