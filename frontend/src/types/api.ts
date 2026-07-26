export interface BedForecastResponse {
  state: string;
  ward_type: string;
  forecast: ForecastDataPoint[];
  status: 'ml_model' | 'db_trend' | 'estimated';
}

export interface ForecastDataPoint {
  year?: number;
  month?: number;
  month_name?: string;
  predicted_beds?: number;
  available_beds?: number;
  total_beds?: number;
  occupancy_rate?: number;
}

export interface MortalityResponse {
  state?: string;
  cause?: string;
  death_rate?: number;
  total_deaths?: number;
  forecast?: MortalityForecastPoint[];
  risk_clusters?: MortalityRiskCluster[];
  status?: 'ml_model' | 'db_trend' | 'estimated';
}

export interface MortalityForecastPoint {
  year: number;
  month: number;
  predicted_deaths: number;
  lower_bound?: number;
  upper_bound?: number;
}

export interface MortalityRiskCluster {
  district: string;
  state: string;
  death_rate: number;
  risk_cluster: string;
}

export interface DistrictItem {
  district: string;
  state?: string;
  count?: number;
}

export interface HospitalRankingItem {
  rank: number;
  hospital_name: string;
  state: string;
  district?: string;
  disease: string;
  success_rate: number;
  hospital_score?: number;
  rating?: number;
  total_beds?: number;
  avg_stay_days?: number;
  accreditation?: string;
  hospital_type?: string;
  specialist_count?: number;
}

export interface PandemicScenarioResponse {
  disease: string;
  state: string;
  projection_year: number;
  outbreak_summary: {
    total_confirmed_cases: number;
    total_deaths: number;
    avg_case_fatality_rate: number;
    avg_reproduction_rate: number;
  };
  monthly_breakdown: PandemicMonthlyPoint[];
  current_capacity: {
    total_beds: number;
    available_beds: number;
    icu_capacity: number;
    icu_available: number;
  };
  projected_impact: {
    projected_bed_demand: number;
    projected_icu_demand: number;
    projected_cfr: number;
    available_beds: number;
    bed_occupancy: number;
    bed_shortage: number;
    icu_shortage: number;
  };
  tolerability: {
    risk_score: number;
    risk_level: string;
    verdict: string;
    bed_occupancy_risk: number;
    fatality_risk: number;
    icu_capacity_risk: number;
    bed_demand_risk: number;
  };
  recommendations: string[];
  recommendations_detailed?: { priority: number; message: string; category: string }[];
  lockdown_recommended?: boolean;
  yearly_r0_trend?: { year: number; avg_r0: number; avg_cfr: number; total_cases: number }[];
  hospitals_at_risk: HospitalRiskItem[];
  r0_source?: string;
}

export interface PandemicMonthlyPoint {
  year: number;
  month: string;
  confirmed_cases: number;
  deaths: number;
  r0?: number;
  cfr?: number;
}

export interface HospitalRiskItem {
  name: string;
  district: string;
  type: string;
  beds: number;
  icu_beds: number;
  specialists: number;
}

export interface PatientRecord {
  id: number;
  patient_name: string;
  age: number;
  blood_group: string;
  gender: string;
  state: string;
  district?: string;
  pre_existing_conditions?: string;
}

export interface PatientDetailData extends PatientRecord {
  vaccine_history?: VaccineRecord[];
  travel_history?: TravelRecord[];
  family_history?: FamilyRecord[];
}

export interface VaccineRecord {
  vaccine_name: string;
  dose_number: number;
  vaccination_date?: string;
  virus_name?: string;
  effectiveness?: number;
}

export interface TravelRecord {
  from_location: string;
  to_location: string;
  travel_date?: string;
  return_date?: string;
  purpose?: string;
}

export interface FamilyRecord {
  relationship: string;
  condition: string;
  age_at_diagnosis?: number;
  is_deceased?: boolean;
}

export interface PatientRiskResponse {
  risk_score: number;
  risk_score_pct?: number;
  risk_level: string;
  features: RiskFeature[];
}

export interface RiskFeature {
  name: string;
  value: number;
  weight: number;
  category: string;
}

export interface StatsResponse {
  states: number;
  districts: number;
  hospitals: number;
  beds: number;
  mortality_records: number;
  patients: number;
}

export interface LocationStatsResponse {
  state?: string;
  district?: string;
  hospitals: {
    total: number;
    avg_success_rate?: number;
    avg_score?: number;
    best_hospital?: { name: string; score: number };
    fatality_rate?: number;
  };
  beds: {
    total_beds: number;
    available_beds?: number;
    avg_occupancy?: number;
    ward_breakdown?: Record<string, number>;
  };
  mortality: {
    total_deaths: number;
    avg_death_rate?: number;
    total_population?: number;
  };
}

export interface ChatResponse {
  response: string;
  intent_detected: string;
  entities_detected: {
    disease: string | null;
    state: string | null;
    virus: string | null;
    patient_id: number | null;
  };
  context_used: string[];
  ai_available: boolean;
  ai_error?: string;
}

export interface ChatSuggestion {
  id: number;
  text: string;
  topic: string;
  priority: number;
}
