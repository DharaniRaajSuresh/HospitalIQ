# ADVERSARIAL RED-TEAMING EVASION LOG
**Independent Adversarial Audit Suite for Testing Detector Robustness**

- **Author**: Red-Team Adversary (Dhivyashree S. & External Audit Team; independent of AST-TIV / PSAP core detector authorship)
- **Target System**: Auditing Protocol (Phase 1 PSAP, Phase 2 AST-TIV, Phase 3 DTEFV)
- **Detector Freeze Commit**: `a615d1c` (frozen before adversarial test generation)
- **Design Intent**: Construct 3–5 non-trivial evasion variants per defect archetype designed to challenge known architectural limitations of static single-file AST parsing, heuristic threshold boundaries ($\tau_{AR} = 0.50$), intermediate dataflow joins, and branch coverage limits.

---

## Adversarial Evasion Cases Specification (N=32)

| Case ID | Archetype | Intended Evasion Strategy | Target Vulnerability | Calibration / Mechanism | Expected Outcome |
|---|---|---|---|---|---|
| `E1_1` | M2: Formula | Single-file algebraic formula | Baseline check | `y = X[:, 0] * 2.5 + X[:, 1]` | Detected (Phase 2 AST) |
| `E1_2` | M2: Formula | Cross-module helper delegation | Single-file AST scope | Formula computed in `ext_calc.py:compute_target()` | **Evaded** (AST Slicer blindspot) |
| `E1_3` | M2: Formula | Matrix dot product intrinsic | AST operator pattern | Target computed via `np.dot(X, w)` without binary `+`/`*` | **Evaded** (Operator parser miss) |
| `E1_4` | M2: Formula | DataFrame lambda abstraction | AST assignment analysis | Target assigned via `df.apply(lambda r: r.a * 2.0)` | **Evaded** (Lambda body opacity) |
| `E2_1` | D5: AR(1) | Collinear noisy decoy dilution | Tree split gain threshold | Added 2 collinear lags; lag-1 gain diluted to 38% (< $\tau_{AR}=0.50$) | **Evaded** (Feature dilution) |
| `E2_2` | D5: AR(1) | Smooth spline lag mix | Feature importance boundary | Diluted lag-1 gain to 46% (just below 0.50) | **Evaded** (Threshold evasion) |
| `E2_3` | D5: AR(1) | Direct autoregressive dominance | Heuristic check | Lag-1 gain at 82% (> 0.50) | Detected (Phase 2 AST/AR) |
| `E2_4` | D5: AR(1) | Distributed lag family | Single-feature vs group | Lags 1-4 each have 22% gain (sum=88%, but each < 50%) | **Evaded** (Single-feature AST miss) |
| `E3_1` | M3: Leakage | Direct column leakage | Def-use tracking | Direct concatenation of same-period deaths | Detected (Phase 2 AST) |
| `E3_2` | M3: Leakage | Indirect dictionary lookup join | Def-use dataflow graph | Target leaked via intermediate dict lookup mapping | **Evaded** (Join graph boundary) |
| `E3_3` | M3: Leakage | Center-aligned rolling lookahead | AST operator tracking | Forward-looking `rolling(3, center=True)` | **Evaded** (Rolling index opacity) |
| `E3_4` | M3: Leakage | Multi-step dataframe merge | Dataflow slicing | Leaked feature merged via multi-step relational join | **Evaded** (Relational join blindspot) |
| `E4_1` | M4: Shuffle | In-place sample shuffle | AST function name check | `df.sample(frac=1.0)` | Detected (Phase 2 AST) |
| `E4_2` | M4: Shuffle | Permutation index shuffling | AST permutation check | `df.iloc[np.random.permutation(len(df))]` | Detected (Phase 2 AST) |
| `E4_3` | M4: Shuffle | Date format string inversion | Semantic ordering check | Month/day swap in date parser causing temporal scramble | **Evaded** (Parser flaw opacity) |
| `E5_1` | M5: DimMismatch | Feature pop before inference | Model signature check | Feature popped from metadata dict | Detected (Phase 3 DTEFV) |
| `E5_2` | M5: DimMismatch | Dynamic kwargs unpacking | Static AST parameter check | Dynamic `**kwargs` unpacking with mismatched length | Detected (Phase 3 DTEFV runtime) |
| `E5_3` | M5: DimMismatch | Silent numpy rank broadcast | Input tensor shape check | `X[:, None]` broadcasting to 2D with wrong semantic width | **Evaded** (Shape contract bypass) |
| `E6_1` | M6: MetaCrash | Corrupted pickle payload | Deserialization check | Type error raised during `pickle.load()` | Detected (Phase 3 DTEFV) |
| `E6_2` | M6: MetaCrash | Deferred method invocation crash | Early-stage load check | Valid pickle, but `predict()` raises missing attribute | Detected (Phase 3 DTEFV probe) |
| `E6_3` | M6: MetaCrash | Missing metadata dictionary key | Schema validator | Key omitted; default `.get()` returns malformed schema | Detected (Phase 3 DTEFV) |
| `E7_1` | M7: Fallback | Broad exception return constant | AST try-except check | `except: return [450]*N` | Detected (Phase 3 AST/DTEFV) |
| `E7_2` | M7: Fallback | Rare input conditional fallback | Probing test coverage | Fallback triggered only if `age > 98` (rare input) | **Evaded** (Incomplete branch probe) |
| `E7_3` | M7: Fallback | Fallback to cached state mean | Invariance detection | Returns historical state average from SQLite cache | Detected (Phase 3 DTEFV probe) |
| `E7_4` | M7: Fallback | Cross-module exception wrapper | Single-file AST scope | Fallback handler defined in imported middleware | **Evaded** (Cross-module AST limit) |
| `E8_1` | M8: ConstInput | Feature column overwrite | AST assign check | `X[:, 3] = 0.0` | Detected (Phase 3 AST) |
| `E8_2` | M8: ConstInput | Dead-code feature assignment | Gradient sensitivity probe | Feature assigned in dead branch; active uses constant | Detected (Phase 3 DTEFV probe) |
| `E8_3` | M8: ConstInput | Dynamic dictionary key deletion | AST subscript check | `del kwargs['feature_name']` in helper function | **Evaded** (Dynamic dict opacity) |
| `E9_1` | M9: Route | Unmounted API router | AST route check | Missing `app.include_router(audit_router)` | Detected (Phase 2 AST) |
| `E9_2` | M9: Route | Dynamic ASGI middleware router | AST decorator check | Route handled via custom ASGI middleware dispatcher | **Evaded** (Middleware dispatch blindspot) |
| `E9_3` | M9: Route | Environment-guarded route | Static AST execution | Route guarded by `if os.getenv('ENABLE_AUDIT')=='1'` | **Evaded** (Static config blindspot) |
| `E9_4` | M9: Route | Wildcard regex path catch-all | Route endpoint match | Route matched by catch-all router returning 404 dynamically | Detected (Phase 2 route contract) |
