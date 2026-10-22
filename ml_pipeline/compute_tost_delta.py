import math
from scipy import stats

def compute_tost():
    n = 30
    df = n - 1
    d_bar = -0.08
    se = 1.25

    results = {}
    margins = [5.0, 2.0]
    for m in margins:
        t1 = (d_bar - (-m)) / se
        p1 = 1 - stats.t.cdf(t1, df=df)
        t2 = (d_bar - m) / se
        p2 = stats.t.cdf(t2, df=df)
        p_tost = max(p1, p2)
        results[f"sesoi_{m}"] = {
            "margin_pp": m,
            "t1": float(t1),
            "p1": float(p1),
            "t2": float(t2),
            "p2": float(p2),
            "p_tost": float(p_tost)
        }
        print(f"SESOI +- {m:.1f} percentage points:")
        print(f"  t1 = {t1:.4f} (p1 = {p1:.6e})")
        print(f"  t2 = {t2:.4f} (p2 = {p2:.6e})")
        print(f"  p_TOST = {p_tost:.6e}")

    t_alpha = stats.t.ppf(0.95, df=df)
    t_beta = stats.t.ppf(0.80, df=df)
    mdes_onesided = (t_alpha + t_beta) * se

    t_crit_two = stats.t.ppf(0.975, df=df)
    mdes_twosided = (t_crit_two + t_beta) * se

    print(f"\nProspective MDES (80% power, df={df}, SE={se}%):")
    print(f"  One-sided TOST formulation: MDES = ({t_alpha:.3f} + {t_beta:.3f}) * {se:.2f} = {mdes_onesided:.2f} percentage points")
    print(f"  Two-sided convention:        MDES = ({t_crit_two:.3f} + {t_beta:.3f}) * {se:.2f} = {mdes_twosided:.2f} percentage points")

if __name__ == '__main__':
    compute_tost()
