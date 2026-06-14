// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Activity, ShieldAlert, Syringe, Plane, Users, AlertTriangle, Info, XCircle } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import { getPatient, getPatientRisk } from '../api';

const VIRUS_NAMES = ["COVID-19","Ebola","H1N1","Marburg","Nipah","SARS"];

export default function PatientDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [virus, setVirus] = useState('COVID-19');
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [riskLoading, setRiskLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getPatient(id).then(d => setData(d))
      .catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [id]);

  const computeRisk = () => {
    setRiskLoading(true);
    setRisk(null);
    getPatientRisk(id, virus).then(d => setRisk(d))
      .catch(e => setError(e.message)).finally(() => setRiskLoading(false));
  };

  if (loading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin"></div></div>;
  if (!data) return <div className="text-center py-20 text-gray-400">Patient not found</div>;

  const { patient, vaccine_history, travel_history, family_history } = data;

  const riskGauge = (val, label) => {
    if (val === undefined || val === null) return null;
    const pct = val * 100;
    const color = pct < 20 ? 'bg-emerald-500' : pct < 40 ? 'bg-amber-500' : pct < 60 ? 'bg-orange-500' : 'bg-rose-500';
    return (
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400"><span>{label}</span><span>{pct.toFixed(1)}%</span></div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} className={`h-full rounded-full ${color}`} />
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <Link to="/dashboard/patients" className="inline-flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Patients
      </Link>
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 rounded-lg px-4 py-2 mt-2">
          <XCircle className="w-4 h-4 flex-shrink-0" /> {error}
        </div>
      )}

      {/* Patient Info */}
      <GlassCard>
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center text-xl font-bold text-white flex-shrink-0">
            {patient.patient_name?.charAt(0) || '?'}
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{patient.patient_name}</h1>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 text-sm">
              <div><span className="text-gray-500">Age</span><p className="text-white">{patient.age || 'N/A'}</p></div>
              <div><span className="text-gray-500">Blood Group</span><p className="text-white font-mono">{patient.blood_group || 'N/A'}</p></div>
              <div><span className="text-gray-500">Gender</span><p className="text-white">{patient.gender || 'N/A'}</p></div>
              <div><span className="text-gray-500">DOB</span><p className="text-white">{patient.dob || 'N/A'}</p></div>
              <div><span className="text-gray-500">State</span><p className="text-white">{patient.state || 'N/A'}</p></div>
              <div><span className="text-gray-500">District</span><p className="text-white">{patient.district || 'N/A'}</p></div>
              <div className="col-span-2"><span className="text-gray-500">Contact</span><p className="text-white font-mono text-xs">{patient.contact || 'N/A'}</p></div>
            </div>
            {patient.pre_existing_conditions && (
              <div className="mt-3 flex items-start gap-2 text-sm">
                <Activity className="w-4 h-4 text-amber-400 mt-0.5" />
                <div><span className="text-gray-500">Pre-existing Conditions:</span><p className="text-amber-300">{patient.pre_existing_conditions}</p></div>
              </div>
            )}
          </div>
        </div>
      </GlassCard>

      {/* Risk Prediction */}
      <GlassCard>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" /> Pandemic Risk Assessment
        </h2>
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end mb-4">
          <div className="flex-1">
            <label className="text-xs text-gray-500 mb-1 block">Select Virus</label>
            <select value={virus} onChange={e => setVirus(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg py-2.5 px-4 text-sm text-white focus:outline-none focus:border-cyan-500">
              {VIRUS_NAMES.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <button onClick={computeRisk} disabled={riskLoading}
            className="px-5 py-2.5 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 flex items-center gap-2 whitespace-nowrap">
            {riskLoading ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <ShieldAlert className="w-4 h-4" />}
            Assess Risk
          </button>
        </div>

        {risk && !risk.error && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">Risk Level:</span>
              <span className={`text-lg font-bold px-3 py-1 rounded-lg ${
                risk.risk_level === 'Low' ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20' :
                risk.risk_level === 'Moderate' ? 'text-amber-400 bg-amber-500/10 border border-amber-500/20' :
                risk.risk_level === 'Elevated' ? 'text-orange-400 bg-orange-500/10 border border-orange-500/20' :
                risk.risk_level === 'High' ? 'text-rose-400 bg-rose-500/10 border border-rose-500/20' :
                'text-red-400 bg-red-500/10 border border-red-500/20'
              }`}>{risk.risk_level}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {riskGauge(risk.risk_score, 'Overall Risk Score')}
              {riskGauge(risk.hospitalization_prob, 'Hospitalization Probability')}
              {riskGauge(risk.mortality_prob, 'Mortality Probability')}
            </div>
            {risk.virus_info && (
              <div className="text-xs text-gray-400 border-t border-gray-700 pt-3 mt-3">
                <span className="text-gray-500">Virus: {risk.virus_name}</span>
                <span className="ml-4">Fatality: {(risk.virus_info.fatality_rate * 100).toFixed(1)}%</span>
                <span className="ml-4">R₀: {risk.virus_info.reproductive_rate}</span>
                <span className="ml-4">Transmission: {risk.virus_info.transmission_mode}</span>
                <span className="ml-4">Vaccine: {risk.virus_info.vaccine_available ? `Yes (${(risk.virus_info.vaccine_effectiveness * 100).toFixed(0)}% eff)` : 'No'}</span>
              </div>
            )}
          </motion.div>
        )}
        {risk && risk.error && <p className="text-rose-400 text-sm">{risk.error}</p>}
      </GlassCard>

      {/* Vaccine History */}
      <GlassCard>
        <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <Syringe className="w-5 h-5 text-emerald-400" /> Vaccine History ({vaccine_history.length})
        </h2>
        {vaccine_history.length === 0 ? (
          <p className="text-gray-500 text-sm">No vaccination records</p>
        ) : (
          <div className="space-y-2">
            {vaccine_history.map(v => (
              <div key={v.id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div>
                  <p className="text-white text-sm font-medium">{v.vaccine_name}</p>
                  <p className="text-xs text-gray-500">Dose {v.dose_number} | {v.vaccination_date} | {v.hospital_name || 'N/A'}</p>
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {v.virus_name || 'General'} {v.effectiveness ? `(${(v.effectiveness * 100).toFixed(0)}%)` : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      {/* Travel History */}
      <GlassCard>
        <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <Plane className="w-5 h-5 text-cyan-400" /> Travel History ({travel_history.length})
        </h2>
        {travel_history.length === 0 ? (
          <p className="text-gray-500 text-sm">No travel records</p>
        ) : (
          <div className="space-y-2">
            {travel_history.map(t => (
              <div key={t.id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div>
                  <p className="text-white text-sm">{t.from_location} → {t.to_location}</p>
                  <p className="text-xs text-gray-500">{t.travel_date} to {t.return_date} | {t.purpose}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      {/* Family History */}
      <GlassCard>
        <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <Users className="w-5 h-5 text-violet-400" /> Family History ({family_history.length})
        </h2>
        {family_history.length === 0 ? (
          <p className="text-gray-500 text-sm">No family history records</p>
        ) : (
          <div className="space-y-2">
            {family_history.map(f => (
              <div key={f.id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div>
                  <p className="text-white text-sm"><span className="text-gray-400">{f.relationship}:</span> {f.condition}</p>
                  <p className="text-xs text-gray-500">Diagnosed at age {f.age_at_diagnosis} {f.is_deceased ? '| Deceased' : ''}</p>
                </div>
                {f.is_deceased && <AlertTriangle className="w-4 h-4 text-rose-400" />}
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}

