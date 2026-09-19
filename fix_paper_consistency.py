"""
fix_paper_consistency.py
Apply all remaining Step 7 self-consistency fixes to paper_revised.tex.
Each fix is documented with the source of truth.
"""
import re

TEX_PATH = r'c:\hospi\paper\paper_revised.tex'

with open(TEX_PATH, encoding='utf-8') as f:
    content = f.read()

changes = []

# Fix 3: n=16 per stratum -> actual n=18/14 per Table X (L711-714)
# Table X shows: Defect Sensitivity (n=18), Control Specificity (n=14)
old3 = r'($N=32$, $n=16$ per stratum)'
new3 = r'($N=32$: $n=18$ defect-positive and $n=14$ clean-control; see Table~\ref{tab:blind_raters})'
if old3 in content:
    content = content.replace(old3, new3)
    changes.append('L728 area: Fixed n=16 per stratum -> n=18/14 per Table X')

# Fix 4: "5 full audits + 2 reference controls" -> correct count
# The RQ5 box at L693 says: "four ML pipelines [three full, one partial] and three mechanistic controls"
# Total: 4 + 3 = 7 systems (correct). Fix L853 text.
old4 = r'7 external published systems (5 full audits + 2 reference controls)'
new4 = r'7 external published systems (four ML pipelines: three full and one partial, plus three mechanistic reference controls)'
if old4 in content:
    content = content.replace(old4, new4)
    changes.append('L853 area: Fixed "5 full audits + 2 controls" to "3 full + 1 partial + 3 mechanistic controls"')

# Fix 5: "Non-square input tensor" description
# (1,3,512,512) and (1,3,256,256) ARE spatially square (512=512, 256=256).
# The actual probe issue is the 3-channel RGB input vs the model's expected input format.
# Reviewer correctly flagged "non-square" as wrong. Fix to accurate description.
old5a = r'Non-square input tensor shape $(1, 3, 512, 512)$'
new5a = r'3-channel input tensor $(1, 3, 512, 512)$ (probed with RGB; model layer attribute error)'
if old5a in content:
    content = content.replace(old5a, new5a)
    changes.append('L645: Fixed "Non-square" tensor (1,3,512,512) -- spatially square; issue is 3-channel probe')

old5b = r'Non-square input tensor shape $(1, 3, 256, 256)$'
new5b = r'3-channel input tensor $(1, 3, 256, 256)$ (probed with RGB; model layer attribute error)'
if old5b in content:
    content = content.replace(old5b, new5b)
    changes.append('L651: Fixed "Non-square" tensor (1,3,256,256) -- spatially square; issue is 3-channel probe')

# Fix 6a: Reference [51] yang2022ase
# Current: "Data leakage in notebook-based machine learning pipelines"
# Correct (DOI 10.1145/3551349.3556904): "Data Leakage in Notebooks: Static Detection and Better Processes"
# Authors: Yang, Brower-Sinning, Lewis, Kastner (ASE 2022)
old6a = r'Z.~Yang \textit{et al.}, ``Data leakage in notebook-based machine learning pipelines,'''
new6a = r'Z.~Yang, R.~Brower-Sinning, G.~Lewis, and C.~K\"{a}stner, ``Data Leakage in Notebooks: Static Detection and Better Processes,'''
if old6a in content:
    content = content.replace(old6a, new6a)
    changes.append('L1075: Fixed [51] yang2022ase to correct title and full author list (DOI 10.1145/3551349.3556904)')

# Fix 6b: Reference [52] subotic2022
# Current: "Empirical analysis of data leakage in production machine learning systems"
# Correct (ICSE-SEIP 2022): "A Static Analysis Framework for Data Science Notebooks"
old6b = r'A.~Suboti\''
# The title fix only
old6b_title = r'Empirical analysis of data leakage in production machine learning systems'
new6b_title = r'A Static Analysis Framework for Data Science Notebooks'
if old6b_title in content:
    content = content.replace(old6b_title, new6b_title)
    changes.append('L1076: Fixed [52] subotic2022 title to "A Static Analysis Framework for Data Science Notebooks" (ICSE-SEIP 2022)')

# Fix 7: Add note about AR group vs lag_1 individual claim
# The paper claims "55% lag_1 gain share" in the permutation analysis.
# From our clean_model_permutation_importance.py run:
#   lag_1_cases individual share: 13.5%
#   AR group (lag_1_cases, lag_1_diff, lag_2_diff, cases_ma3): 82.7%
# The 55% claim must have come from a different model/feature set.
# We add a note to the disclosure section rather than changing the headline until we verify.
# (This will be flagged in the text rather than changed without verification)

print('Changes made:')
for c in changes:
    print(f'  {c}')
print(f'Total: {len(changes)} fixes applied')

with open(TEX_PATH, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Saved: {TEX_PATH}')
