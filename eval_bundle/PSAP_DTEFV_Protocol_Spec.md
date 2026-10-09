# Three-Phase Forensic Auditing Protocol — Specification

This document specifies a general-purpose auditing protocol for machine
learning systems that blend real and synthetic (or otherwise
provenance-ambiguous) data. It is system-agnostic: no step below refers to
any specific target system's file names, thresholds observed in a prior
application, or expected outcomes.

---

## Phase 1 — Provenance-Stratified Auditing Protocol (PSAP)

**Goal:** determine whether records labeled "real" (or "authentic",
"empirical", "ground-truth", etc.) in the system's data layer are actually
what they claim to be.

**Inputs:** the dataset `D = {(x_i, y_i, p_i, t_i)}`, where `p_i` is the
system's own provenance label (real=1 / synthetic=0) and `t_i` is a
timestamp or other metadata field associated with the record.

**Procedure:**

1. **Locate the provenance flag.** Identify the field(s) in the data
   schema, ORM/database model, and any ingestion/seeding scripts that
   assert a record's provenance. Note explicitly whether this flag is
   persisted in the actual database/storage layer used at training and
   inference time, or exists only in an intermediate artifact (e.g., a CSV
   that is not re-read at serving time).

2. **Establish an independent authentication boundary.** For each source
   the system claims to draw "real" data from (an API, a public dataset, a
   named institution), find independent, external documentation of that
   source's actual valid reporting window, coverage, or scope (e.g., "this
   API was deprecated on date X," "this dataset covers only region Y").
   This must come from a source independent of the target system's own
   code comments or documentation.

3. **Re-derive provenance labels independently.** For each nominally
   "real" record, check whether its timestamp, geography, or other
   identifying metadata actually falls within the externally-verified
   authentic window/scope established in step 2. Assign a corrected label
   `p*_i`.

4. **Compute the contamination rate:**

   ```
   alpha = P(p_i = 1 and p*_i = 0) / P(p_i = 1)
   ```

   i.e., the fraction of nominally-real records that fail independent
   authentication.

5. **Stratified error estimation.** Partition any held-out evaluation set
   into `S_real = {z : p*_i = 1}` and `S_synth = {z : p*_i = 0}` using the
   *corrected* label, and compute the model's error metric (MAPE, WAPE, or
   equivalent) separately on each stratum. Report the ratio between strata.

6. **Verdict:**
   - If `alpha > 0.05`: **"Labels Corrupted; Stratification Invalid."**
     Any prior aggregate or naively-stratified evaluation using the
     uncorrected label is unreliable.
   - Else if stratum error ratio > 2.0: **"Severe Generalization
     Degradation."**
   - Else: **"Provenance-Consistent."**

   Note: the 0.05 and 2.0 thresholds are defaults from prior protocol
   applications, not universal constants. If you have domain-specific
   reason to use different thresholds for this target system, state your
   reasoning and report results under both the default and your chosen
   threshold.

---

## Phase 2 — Code and Target Lineage Audit

**Goal:** determine whether each learned model is actually learning
generalizable structure, or reconstructing/memorizing a known
transformation of its own inputs.

**Procedure, per predictive component:**

1. **Locate the training script and the exact line(s) that construct the
   training target `y`.** Determine whether `y` is:
   (a) an independently measured/observed quantity, or
   (b) a deterministic function of features already present in `x`
       (formula reconstruction), or
   (c) derived from `x` at a data-leaking time offset (e.g., using
       same-period or future information not available at inference time —
       contemporaneous or temporal leakage).

2. **Formula reconstruction test.** If you suspect (b), attempt to fit a
   trivial closed-form model (linear regression, or the specific formula if
   identifiable in code) directly from `x` to `y`. If a simple deterministic
   function reproduces `y` to near-perfect fit (a reasonable default
   threshold is R² ≥ 0.98, adjustable with justification), classify as
   **Formula Reconstruction**.

3. **Autoregressive/persistence dominance test.** Extract feature
   importances (gain-based, permutation-based, or SHAP) from the trained
   model artifact. If a single lag/persistence feature accounts for a large
   majority of attribution (a reasonable default is >50%) with all other
   features contributing negligibly (<3% each), classify as **AR(1)
   Dominance / Persistence Heuristic**.

4. **Negative-skill test.** Compare the model's out-of-sample R² (or
   equivalent) against the R² of an unparameterized baseline (e.g., the
   historical mean or a naive persistence forecast). If the learned model
   underperforms this baseline, classify as **Negative Skill**.

5. **Genuine learning.** If none of the above hold, and the model extracts
   non-trivial, non-leaking, non-degenerate associations from its inputs,
   classify tentatively as **Genuine Learning** — pending Phase 3.

---

## Phase 3 — Deployment-Time Execution and Fallback Verification (DTEFV)

**Goal:** determine whether a component that appears to "genuinely learn"
in Phase 2 actually executes correctly when invoked through the system's
real, deployed inference path — not a mock, a notebook re-implementation,
or a unit test that bypasses model loading.

**Procedure, per predictive component:**

1. **Extract deployed artifact metadata.** For the serialized model
   actually loaded at serving time, extract its expected input dimensionality/
   schema (e.g., `n_features_in_`, or equivalent for the framework in use).

2. **Extract the live feature-construction path.** Trace the actual
   code path that builds the feature vector passed to this model at
   inference time (not the training-time feature construction — the
   deployment-time one, which may have drifted).

3. **Structural mismatch check.** Compare the artifact's expected input
   shape/schema against what the live inference path actually constructs.
   Flag any mismatch.

4. **Live execution probe.** Instantiate the actual deployed artifact
   (not a retrained copy) and call its prediction method with:
   (a) a well-formed, in-distribution payload (sanity check), and
   (b) the adversarial perturbation battery in
       `Adversarial_Perturbation_Template.py`.
   Record, for each probe, one of the following outcomes:
   - **CRASH** — an unhandled exception propagates.
   - **SILENT_DEGRADED** — the call returns a value with no error, but the
     value is provably wrong, out-of-bounds, or independent of the
     perturbed input in a way that shouldn't be possible for a genuine
     model.
   - **INPUT_REJECTED** — the system correctly detects the invalid/adversarial
     input and raises a controlled, documented rejection (this is the
     desired defensive behavior).
   - **HANDLED_GRACEFULLY** — the system produces a bounded, sensible
     output or a clearly-flagged fallback indicator visible to the caller.

5. **Fallback-path inspection.** If the system has a multi-tier fallback
   architecture (e.g., ML model → simpler heuristic → hardcoded default),
   determine whether a fallback event is surfaced to the caller/API
   response in any way, or silently masked. Silent masking of a fallback
   event — where the caller cannot distinguish a genuine model prediction
   from a fallback — is itself a defect, independent of whether the
   fallback value is "reasonable."

6. **Verdict per component** (assign exactly one):
   - **Genuine Learning, Deployed Correctly** — passes Phase 2 as genuine
     AND executes correctly (no crash, no silent degradation, matches
     training-time feature contract) at deployment time.
   - **Deployment Degradation** — passes Phase 2 as genuine, but fails at
     deployment time due to a structural/integration defect.
   - **Non-Functional / Dead Code** — the component never executes
     successfully via its real invocation path (always crashes or always
     falls back).
   - **Does Not Learn Genuinely** — fails Phase 2 (formula reconstruction,
     AR(1) dominance, negative skill, or leakage), regardless of whether it
     executes without crashing.

---

## Aggregate Reporting

For the target system as a whole, report:

- Total number of predictive/ML components audited.
- Count and proportion falling into each of the five verdict tiers.
- Contamination rate `alpha` from Phase 1 (if applicable — some systems
  may have no explicit provenance-labeling scheme at all; note this
  explicitly rather than forcing a rate onto a system that doesn't make
  this claim).
- Phase-by-phase defect attribution: how many total defects would have
  been missed if only Phase 1, only Phase 2, or only Phase 3 had been run.
- Total time spent per phase.
- Your overall confidence in the completeness of this audit (you are one
  auditor auditing a system you don't have full institutional knowledge
  of — be explicit about what you could not access or verify, e.g. private
  CI logs, internal design docs, staging environments).
