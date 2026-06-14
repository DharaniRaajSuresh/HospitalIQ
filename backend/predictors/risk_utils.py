RISK_THRESHOLD_CRITICAL = 150
RISK_THRESHOLD_HIGH = 100
RISK_THRESHOLD_MODERATE = 60


def assign_risk_level(death_rate: float) -> str:
    if death_rate > RISK_THRESHOLD_CRITICAL:
        return "Critical"
    elif death_rate > RISK_THRESHOLD_HIGH:
        return "High Risk"
    elif death_rate > RISK_THRESHOLD_MODERATE:
        return "Moderate"
    else:
        return "Low Risk"


def compute_risk_score(death_rate: float) -> int:
    if death_rate > RISK_THRESHOLD_CRITICAL:
        score = 85 + min(15, (death_rate - RISK_THRESHOLD_CRITICAL) / 3)
    elif death_rate > RISK_THRESHOLD_HIGH:
        score = 65 + ((death_rate - RISK_THRESHOLD_HIGH) / (RISK_THRESHOLD_CRITICAL - RISK_THRESHOLD_HIGH)) * 20
    elif death_rate > RISK_THRESHOLD_MODERATE:
        score = 40 + ((death_rate - RISK_THRESHOLD_MODERATE) / (RISK_THRESHOLD_HIGH - RISK_THRESHOLD_MODERATE)) * 25
    else:
        score = 15 + (death_rate / RISK_THRESHOLD_MODERATE) * 25
    return min(100, int(score))
