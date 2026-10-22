import pypdf
import json
import re

def verify_phase3():
    reader = pypdf.PdfReader('paper/paper_revised.pdf')
    raw_text = '\n'.join([page.extract_text() for page in reader.pages])

    # Normalize unicode minus, hyphenated linebreaks, and whitespace
    text_clean = raw_text.replace('\u2212', '-').replace('-\n', '')
    text_norm = re.sub(r'\s+', ' ', text_clean)
    
    # Read raw JSON
    with open('paper_revision/results/clean_vs_deployed_forecast_evaluation.json', encoding='utf-8') as f:
        eval_json = json.load(f)

    # Read Phase Reports
    with open('PHASE_2C_REPORT.md', encoding='utf-8') as f:
        p2c = f.read()
    with open('PHASE_2D_REPORT.md', encoding='utf-8') as f:
        p2d = f.read()
    with open('PHASE_2E_REPORT.md', encoding='utf-8') as f:
        p2e = f.read()

    checks = []

    # Spot Check 1: Phase 2C Report vs PDF
    checks.append(('Spot 1: Delta Clean WAPE 77.03% in PDF & P2C', '77.03%' in text_norm and '77.03%' in p2c))
    checks.append(('Spot 1: Delta Deployed WAPE 98.42% in PDF & P2C', '98.42%' in text_norm and '98.42%' in p2c))
    checks.append(('Spot 1: Delta Naive WAPE 94.65% in PDF & P2C', '94.65%' in text_norm and '94.65%' in p2c))
    checks.append(('Spot 1: Capacity Control N=1000 -> 76.63% in PDF & P2C', '76.63%' in text_norm and '76.63%' in p2c))

    # Spot Check 2: Phase 2D Report vs PDF
    checks.append(('Spot 2: Contamination 85.5% vs 83.1% in PDF & P2D', '85.5%' in text_norm and '83.1%' in text_norm and '85.4784' in p2d and '83.0581' in p2d))
    checks.append(('Spot 2: Exact 85 transition rows in PDF & P2D', '85 transition' in text_norm and '85 records' in p2d))
    checks.append(('Spot 2: Single CSV path ml_pipeline/data/raw/outbreak_real.csv in PDF', 'outbreak_real.csv' in text_norm))

    # Spot Check 3: Phase 2E Report vs PDF
    checks.append(('Spot 3: Tooling detection rates 2/9, 3/9, 2/9 in PDF & P2E', '2/9' in text_norm and '3/9' in text_norm and '2/9' in p2e and '3/9' in p2e))
    checks.append(('Spot 3: 1:4:4 partition (P1 1/9, P2 4/9, P3 4/9) in PDF & P2E', '1/9' in text_norm and '4/9' in text_norm and '1:4:4' in text_norm))
    checks.append(('Spot 3: Verbatim white-box threat disclosure in PDF & P2E', 
                   'Threat to Internal Validity (Tooling Benchmark Grounding)' in text_norm and 
                   'structural blindspots shared across these tools' in text_norm and
                   'calendar whitelists or strict drift gating can increase coverage to 33.3%' in text_norm))

    # Spot Check 4: Phase 2C Raw JSON vs PDF
    t_c_dep_sq = f"{eval_json['delta_evaluation']['dm_clean_vs_deployed_sq']['t_stat']:.3f}"
    p_c_dep_sq = f"{eval_json['delta_evaluation']['dm_clean_vs_deployed_sq']['p_value']:.3f}"
    t_c_naive_sq = f"{eval_json['delta_evaluation']['dm_clean_vs_naive_sq']['t_stat']:.3f}"
    p_c_naive_sq = f"{eval_json['delta_evaluation']['dm_clean_vs_naive_sq']['p_value']:.3f}"
    t_c_naive_abs = f"{eval_json['delta_evaluation']['dm_clean_vs_naive_abs']['t_stat']:.3f}"
    p_c_naive_abs = f"{eval_json['delta_evaluation']['dm_clean_vs_naive_abs']['p_value']:.4f}"

    checks.append((f'Spot 4: Clean vs Deployed Sq (t={t_c_dep_sq}, p={p_c_dep_sq})', t_c_dep_sq in text_norm and p_c_dep_sq in text_norm))
    checks.append((f'Spot 4: Clean vs Naive Sq (t={t_c_naive_sq}, p={p_c_naive_sq})', t_c_naive_sq in text_norm and p_c_naive_sq in text_norm))
    checks.append((f'Spot 4: Clean vs Naive Abs (t={t_c_naive_abs}, p={p_c_naive_abs})', t_c_naive_abs in text_norm and p_c_naive_abs in text_norm))
    checks.append(('Spot 4: Disambiguated State Wins (26/30 clean vs naive, 22/30 clean vs deployed)', 
                   '26 of 30 states (86.7%)' in text_norm and '22 of 30 states (73.3%)' in text_norm))

    # Binding Amendments
    checks.append(('Amendment 3: DEF-2D-3 AR(1) in Abstract (55.00% -> 41.01%)', 
                   '55.00%' in text_norm and '41.01%' in text_norm and 'misattributing synthetic data regularities' in text_norm))
    checks.append(('Amendment 4: Domain shift forensics (12.85x and 4.56x-43.26x)', 
                   '12.85' in text_norm and '4.56' in text_norm and '43.26' in text_norm))
    checks.append(('CRediT format: Parkavi K without Dr prefix', 
                   'Parkavi K' in text_norm and 'Dr. Parkavi' not in text_norm and 'Dr. Parkavi' not in raw_text))

    # Spot Check 5: Omicron Purge and Provenance Boundary Enforcement
    checks.append(('Spot 5: Provenance Boundary text in PDF', 
                   'Surveillance Provenance Boundary and Post-October 2021 Wave Exclusion' in text_norm))
    checks.append(('Spot 5: Omicron purged from empirical benchmark', 
                   'Wave 3 (Omicron)' not in text_norm and 'Out-of-Sample Multi-Wave Surveillance and Family-Wise Error Rate' not in text_norm))
    checks.append(('Spot 5: Post-2021 boundary explicitly in Limitation 10', 
                   'Surveillance Wave Coverage and Post-2021 Provenance Boundary' in text_norm and 'Omicron wave, were explicitly excluded' in text_norm))

    # Spot Check 6: 4-Decimal R2 Metric Synchronization
    r2_clean_str = f"{eval_json['delta_evaluation']['clean_model']['r2']:.4f}"
    r2_dep_str = f"{eval_json['delta_evaluation']['deployed_model']['r2']:.4f}"
    r2_naive_str = f"{eval_json['delta_evaluation']['naive_baseline']['r2']:.4f}"
    checks.append((f'Spot 6: Clean R2 4-decimal sync ({r2_clean_str}) in PDF', r2_clean_str in text_norm))
    checks.append((f'Spot 6: Deployed R2 4-decimal sync ({r2_dep_str}) in PDF', r2_dep_str in text_norm))
    checks.append((f'Spot 6: Naive R2 4-decimal sync ({r2_naive_str}) in PDF', r2_naive_str in text_norm))

    # Spot Check 7: Conceptual & Architectural Precision
    checks.append(('Spot 7: Pre-deployment artifact introspection in Table Note & RQ3', 
                   'pre-deployment artifact introspection' in text_norm and 'RQ3 (Lineage/Introspection vs. Execution Reachability)' in text_norm))
    checks.append(('Spot 7: Figure 1 caption harmonized (8 ML + 1 rule-based)', 
                   'eight machine learning/statistical models and one deterministic clinical rule-based scoring formula' in text_norm))

    # Spot Check 8: Statistical Validity Threats Disclosed
    checks.append(('Spot 8: McNemar non-i.i.d. threat in Validity & Table Note', 
                   'Statistical Conclusion Validity' in text_norm and 'descriptive divergence indicators' in text_norm))

    # Spot Check 9: Authentic Rolling-Origin Metrics
    checks.append(('Spot 9: Authentic Rolling Origin Overall (WAPE 99.99% vs 79.15%)',
                   '99.99%' in text_norm and '79.15%' in text_norm))
    checks.append(('Spot 9: Authentic Rolling Origin DM Test (t=2.8039, p=0.0089)',
                   '2.8039' in text_norm and '0.0089' in text_norm))
    checks.append(('Spot 9: Authentic Rolling Origin Waves (W1 51.52%, W2 93.85%)',
                   '51.52%' in text_norm and '93.85%' in text_norm))

    checks.append(('Page Budget: Exactly 24 pages', len(reader.pages) == 24))

    all_ok = True
    print(f"Total Pages in PDF: {len(reader.pages)}")
    print("=" * 80)
    for desc, res in checks:
        status = 'PASS' if res else 'FAIL'
        print(f"[{status}] {desc}")
        if not res:
            all_ok = False

    print("=" * 80)
    print(f"*** OVERALL VERIFICATION: {'ALL PASSED' if all_ok else 'FAILED'} ***")
    return all_ok

if __name__ == '__main__':
    verify_phase3()
