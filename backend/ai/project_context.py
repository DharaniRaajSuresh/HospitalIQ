from typing import Any

KNOWN_VIRUSES = ["COVID-19", "Ebola", "H1N1", "Marburg", "Nipah", "SARS"]
KNOWN_VIRUS_ALIASES = {
    "covid": "COVID-19", "corona": "COVID-19", "sarscov2": "COVID-19", "covid-19": "COVID-19",
    "ebola": "Ebola", "ebola virus": "Ebola",
    "h1n1": "H1N1", "swine flu": "H1N1", "swine": "H1N1",
    "marburg": "Marburg", "marburg virus": "Marburg",
    "nipah": "Nipah", "nipah virus": "Nipah",
    "sars": "SARS", "sars-cov": "SARS",
}

PROJECT_CONTEXT: dict[str, Any] = {
    "name": "HospitalIQ v2.0",
    "description": "AI-powered hospital intelligence system for India",
    "capabilities": [
        "Bed availability forecasting using GradientBoosting (R²=0.9756)",
        "Mortality risk analysis using XGBoost with K-Means clustering (R²=0.9493)",
        "Hospital performance ranking using RandomForest (R²=0.9326)",
        "Pandemic risk scoring using RandomForest (R²=0.9806)",
        "Time-series forecasting using XGBoost (Cases/Deaths MAPE ~76%)",
        "Pandemic scenario simulation for 6 diseases (COVID-19, Ebola, H1N1, SARS, Nipah, Marburg)",
    ],
    "data_coverage": "All 30 Indian states, 758 districts",
    "models": ["Bed", "Mortality", "Hospital", "Risk", "Forecast"],
    "schema": {
        "hospital_beds": {
            "description": "Bed availability per hospital per month",
            "columns": ["state", "district", "hospital_name", "ward_type", "total_beds", "available_beds", "occupancy_rate", "recorded_month", "recorded_year"],
            "record_count": 122880,
            "ward_types": ["General", "ICU", "Maternity", "Emergency", "Pediatric"],
        },
        "mortality_records": {
            "description": "Death records by cause, age group, district (monthly)",
            "columns": ["state", "district", "year", "month", "age_group", "cause_of_death", "death_count", "death_rate", "population", "risk_cluster"],
            "record_count": 698880,
            "causes_of_death": ["Accident", "Cancer", "Cardiac", "Infectious", "Maternal", "Neonatal", "Respiratory"],
            "age_groups": ["0-14", "15-30", "31-45", "46-60", "60+"],
            "risk_clusters": ["Low", "Medium", "High", "Critical"],
        },
        "hospital_outcomes": {
            "description": "Hospital performance metrics per disease",
            "columns": ["hospital_id", "hospital_name", "state", "district", "hospital_type", "disease", "total_cases", "success_rate", "avg_stay_days", "hospital_score", "rating", "accreditation", "total_beds", "icu_beds", "specialist_count"],
            "record_count": 162080,
            "diseases": ["Cancer", "Cardiac", "Dengue", "Diabetes", "Hepatitis", "Malaria", "Pneumonia", "Stroke", "Tuberculosis", "Typhoid", "Renal", "Orthopedic"],
            "hospital_types": ["Government", "Private", "Trust", "Corporate"],
        },
        "patient_admissions": {
            "description": "Individual patient admission records",
            "columns": ["patient_id", "admission_date", "discharge_date", "hospital_name", "state", "disease", "age_group", "gender", "admission_type", "outcome", "length_of_stay"],
            "record_count": 140000,
        },
        "pandemic_outbreak": {
            "description": "Pandemic simulation data (monthly) for scenario modeling",
            "columns": ["state", "disease", "year", "month", "cases", "deaths", "r0", "cfr"],
            "record_count": 296638,
            "diseases": ["COVID-19", "Ebola", "H1N1", "Marburg", "Nipah", "SARS"],
        },
        "patients": {
            "description": "Patient demographics with pre-existing conditions",
            "columns": ["patient_name", "age", "blood_group", "gender", "state", "district", "pre_existing_conditions"],
            "record_count": 200000,
        },
        "vaccine_history": {
            "description": "Patient vaccination records per virus",
            "columns": ["patient_id", "vaccine_name", "dose_number", "vaccination_date", "virus_name", "effectiveness"],
            "record_count": 450085,
            "viruses": ["COVID-19", "H1N1", "Hepatitis B", "Seasonal Flu"],
        },
        "travel_history": {
            "description": "Patient travel records for risk assessment",
            "columns": ["patient_id", "from_location", "to_location", "travel_date", "return_date", "purpose"],
            "record_count": 175419,
        },
        "family_history": {
            "description": "Patient family medical history",
            "columns": ["patient_id", "relationship", "condition", "age_at_diagnosis", "is_deceased"],
            "record_count": 151040,
        },
        "virus_registry": {
            "description": "Pandemic virus metadata (fatality rate, R0, vaccine effectiveness)",
            "columns": ["virus_name", "fatality_rate", "reproductive_rate", "incubation_period_days", "transmission_mode", "vaccine_available", "vaccine_effectiveness"],
            "record_count": 6,
            "viruses": KNOWN_VIRUSES,
        },
    },
    "available_states": ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar"],
}

KNOWN_DISEASES = [
    "Cancer", "Cardiac", "Dengue", "Diabetes", "Hepatitis", "Malaria",
    "Pneumonia", "Stroke", "Tuberculosis", "Typhoid",
    "COVID-19", "Ebola", "H1N1", "Marburg", "Nipah", "SARS",
    "Accident", "Infectious", "Maternal", "Neonatal", "Respiratory",
    "Renal", "Orthopedic",
]
KNOWN_DISEASE_ALIASES = {
    "canser": "Cancer", "tumor": "Cancer", "malignancy": "Cancer", "oncology": "Cancer", "cancerous": "Cancer", "carcinoma": "Cancer",
    "cardio": "Cardiac", "heart": "Cardiac", "cardiovascular": "Cardiac", "cardiac arrest": "Cardiac", "heart attack": "Cardiac", "myocardial": "Cardiac", "coronary": "Cardiac",
    "lung": "Respiratory", "breathing": "Respiratory", "pulmonary": "Respiratory", "respiratory infection": "Respiratory", "copd": "Respiratory", "asthma": "Respiratory",
    "tb": "Tuberculosis", "consumption": "Tuberculosis", "tuberculosis": "Tuberculosis",
    "flu": "H1N1", "swine": "H1N1", "influenza": "H1N1", "swine flu": "H1N1",
    "dengue fever": "Dengue", "hemorrhagic": "Dengue", "dengue": "Dengue",
    "covid": "COVID-19", "corona": "COVID-19", "sarscov2": "COVID-19", "covid19": "COVID-19", "coronavirus": "COVID-19", "pandemic": "COVID-19",
    "nipah": "Nipah", "nipah virus": "Nipah",
    "ebola": "Ebola", "ebola virus": "Ebola",
    "marburg": "Marburg", "marburg virus": "Marburg",
    "sars": "SARS", "sars-cov": "SARS", "sars coronavirus": "SARS",
    "diabetes": "Diabetes", "sugar": "Diabetes", "diabetic": "Diabetes", "type 2": "Diabetes", "type 1": "Diabetes",
    "hepatitis": "Hepatitis", "liver": "Hepatitis", "jaundice": "Hepatitis", "hep b": "Hepatitis", "hep c": "Hepatitis",
    "malaria": "Malaria", "vector": "Malaria", "plasmodium": "Malaria",
    "pneumonia": "Pneumonia", "chest infection": "Pneumonia", "lung infection": "Pneumonia",
    "stroke": "Stroke", "brain attack": "Stroke", "cva": "Stroke", "cerebral": "Stroke", "hemorrhage": "Stroke", "paralysis": "Stroke",
    "typhoid": "Typhoid", "enteric": "Typhoid", "salmonella": "Typhoid",
    "accident": "Accident", "injury": "Accident", "trauma": "Accident", "fracture": "Accident",
    "infectious": "Infectious", "infection": "Infectious", "sepsis": "Infectious", "viral": "Infectious", "bacterial": "Infectious",
    "maternal": "Maternal", "pregnancy": "Maternal", "childbirth": "Maternal", "obstetric": "Maternal", "postpartum": "Maternal",
    "neonatal": "Neonatal", "newborn": "Neonatal", "infant": "Neonatal", "birth": "Neonatal",
    "renal": "Renal", "kidney": "Renal", "nephrology": "Renal", "ckd": "Renal", "dialysis": "Renal",
    "orthopedic": "Orthopedic", "ortho": "Orthopedic", "bone": "Orthopedic", "joint": "Orthopedic", "arthritis": "Orthopedic", "spine": "Orthopedic",
}
KNOWN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
    "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar",
]
KNOWN_STATE_ALIASES: dict[str, str] = {
    "ap": "Andhra Pradesh", "andra": "Andhra Pradesh", "andhra": "Andhra Pradesh", "vizag": "Andhra Pradesh", "visakhapatnam": "Andhra Pradesh",
    "delhi": "Delhi", "dilli": "Delhi", "new delhi": "Delhi", "ncr": "Delhi",
    "goa": "Goa", "panaji": "Goa", "panjim": "Goa",
    "gujrat": "Gujarat", "guj": "Gujarat", "ahmedabad": "Gujarat", "gandhinagar": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
    "karnataka": "Karnataka", "karnatak": "Karnataka", "bangalore": "Karnataka", "bengaluru": "Karnataka", "mysore": "Karnataka", "mangalore": "Karnataka",
    "kerala": "Kerala", "kerela": "Kerala", "kochi": "Kerala", "trivandrum": "Kerala", "thiruvananthapuram": "Kerala", "kozhikode": "Kerala", "calicut": "Kerala",
    "maharastra": "Maharashtra", "maharashra": "Maharashtra", "mumbai": "Maharashtra", "bombay": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra", "thane": "Maharashtra", "navi mumbai": "Maharashtra",
    "punjab": "Punjab", "chandigarh": "Punjab", "amritsar": "Punjab", "ludhiana": "Punjab",
    "rajasthan": "Rajasthan", "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "udaipur": "Rajasthan",
    "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu", "chennai": "Tamil Nadu", "madras": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "telangana": "Telangana", "telengana": "Telangana", "hyderabad": "Telangana", "secunderabad": "Telangana",
    "west bengal": "West Bengal", "kolkata": "West Bengal", "bengal": "West Bengal", "calcutta": "West Bengal", "howrah": "West Bengal",
    "bihar": "Bihar", "patna": "Bihar", "gaya": "Bihar",
    "up": "Uttar Pradesh", "uttar pradesh": "Uttar Pradesh", "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh", "varanasi": "Uttar Pradesh", "agra": "Uttar Pradesh",
    "uk": "Uttarakhand", "uttarakhand": "Uttarakhand", "dehradun": "Uttarakhand", "nainital": "Uttarakhand",
    "mp": "Madhya Pradesh", "madhya pradesh": "Madhya Pradesh", "indore": "Madhya Pradesh", "bhopal": "Madhya Pradesh",
    "haryana": "Haryana", "gurugram": "Haryana", "gurgaon": "Haryana", "faridabad": "Haryana",
    "odisha": "Odisha", "orissa": "Odisha", "bhubaneswar": "Odisha", "cuttack": "Odisha",
    "assam": "Assam", "guwahati": "Assam", "dispur": "Assam",
    "jharkhand": "Jharkhand", "ranchi": "Jharkhand", "jamshedpur": "Jharkhand",
}


def get_project_context() -> dict[str, Any]:
    return PROJECT_CONTEXT


def format_project_context(context: dict[str, Any]) -> str:
    lines = [f"# {context['name']}", f"\n{context['description']}", "\n## Capabilities:"]
    for c in context.get("capabilities", []):
        lines.append(f"- {c}")
    lines.append(f"\nData Coverage: {context.get('data_coverage', 'N/A')}")
    lines.append(f"Models: {', '.join(context.get('models', []))}")
    lines.append("\n## Database Tables:")
    for table, info in context.get("schema", {}).items():
        lines.append(f"\n### {table} ({info['record_count']:,} records)")
        lines.append(f"  {info['description']}")
        lines.append(f"  Columns: {', '.join(info['columns'])}")
        for key in ["diseases", "causes_of_death", "ward_types", "hospital_types", "age_groups", "viruses"]:
            if key in info:
                lines.append(f"  {key.replace('_', ' ').title()}: {', '.join(info[key])}")
    lines.append(f"\n## Available States ({len(PROJECT_CONTEXT['available_states'])}):")
    for i in range(0, len(PROJECT_CONTEXT['available_states']), 6):
        lines.append("  " + ", ".join(PROJECT_CONTEXT['available_states'][i:i+6]))
    return "\n".join(lines)
