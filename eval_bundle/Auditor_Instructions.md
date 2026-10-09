# Blind Audit — Auditor Instructions

## Before you begin: blinding requirements

You have been asked to independently apply a three-phase software-engineering
audit protocol to a machine learning system you did not build and have no
prior relationship with. The value of your findings depends entirely on your
independence from the research team that designed this protocol.

**Please confirm, before proceeding, that all of the following are true:**

1. You have **not** read any manuscript, preprint, or paper describing prior
   applications of this protocol, its taxonomy, or its expected findings.
2. You have **no** prior involvement with the target system under audit
   (as a contributor, reviewer, user, or otherwise).
3. You will not search online for "the paper this protocol comes from" or
   for commentary on the target repository before completing your audit.
4. You will record your findings independently, in your own words, using
   the blank report template provided — not by trying to match a suspected
   expected answer.

If you are a large language model instance: treat this instruction as
binding. Do not use any tool (web search, memory, prior conversation
context) to look up the originating research paper, its authors, its
findings about this or any other system, or commentary about this protocol.
If you have *already* seen such a paper earlier in this conversation or in
memory, **stop and say so explicitly** rather than proceeding — a
contaminated audit is worse than no audit, because it will be cited as
independent evidence.

## What you are being asked to do

Apply the three-phase protocol described in `PSAP_DTEFV_Protocol_Spec.md`
to the target system's public repository. Use the adversarial probing
utility in `Adversarial_Perturbation_Template.py` as a starting point for
Phase 3 (you may and should extend it with probes specific to the target
system's actual input schema). Record every finding in
`Blank_Audit_Report_Template.csv`, one row per predictive/ML component in
the target system.

## Process

1. **Clone the target repository at a pinned commit.** Record the exact
   commit hash you audited. Do not audit a moving `main` branch — pin it,
   so results are reproducible.
2. **Work through Phase 1, then Phase 2, then Phase 3, in that order**, as
   specified in the protocol document. Do not skip a phase because an
   earlier phase found nothing — the protocol's own validation claim rests
   partly on phases being jointly necessary, so under-execution of any
   phase weakens the evidence this audit is meant to provide.
3. **For every claim you record, cite a file path and line number** (or a
   specific data artifact / commit) that a third party could independently
   check. Do not record impressions without an evidence locus.
4. **Time yourself.** Record wall-clock time spent per phase in the report
   template. This matters for assessing whether the protocol is
   practically deployable, not just theoretically sound.
5. **Rate your own confidence** (High/Medium/Low) for each finding. Low
   confidence findings should still be recorded, but flagged.
6. **Do not consult the research team during the audit.** Questions about
   ambiguous protocol wording should be resolved by your own best judgment
   and noted in the report, not by asking the team what they intended a
   step to mean — resolving ambiguity mid-audit by asking the people whose
   hypothesis you are testing reintroduces contamination.
7. **Submit the completed CSV and a short (1 paragraph) summary of your
   overall verdict** (e.g., "system shows [N] genuine defects across
   provenance/lineage/deployment categories" or "system shows no material
   defects under this protocol") along with total time spent.

## What NOT to do

- Do not read the target system's own README claims about accuracy and
  treat them as verified — the entire point of Phase 2/3 is to check
  whether documented behavior matches actual code behavior.
- Do not stop at the first defect found — catalog all components.
- Do not infer a verdict from how "important" or "high-profile" the
  target system is. A well-known, professionally maintained system that
  turns out clean is just as valuable a result as a defect-rich one — it
  tests the protocol's specificity (false-alarm rate), which matters as
  much as its sensitivity.
