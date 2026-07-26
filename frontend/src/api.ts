/* Production API client with Bearer token auth (memory-based for XSS security) */

interface CacheEntry {
  data: unknown;
  timestamp: number;
}

interface AuthFetchOptions extends RequestInit {
  headers?: Record<string, string>;
}

interface LoginResponse {
  access_token?: string;
  authenticated?: boolean;
  [key: string]: unknown;
}

interface PaginatedResponse<T> {
  patients?: T[];
  total?: number;
  results?: T[];
  [key: string]: unknown;
}

interface BedForecastParams {
  state: string;
  ward_type: string;
  months_ahead: number;
  year?: string;
}

interface PatientListParams {
  limit?: string;
  skip?: string;
  search?: string;
  state?: string;
}

const API_BASE = '/api/v1';
const PATIENT_API_BASE = '/patient-api/v1';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return (window as unknown as Record<string, string>).__auth_token || null;
}

export function setToken(tok: string | null): void {
  if (typeof window === 'undefined') return;
  if (tok) {
    (window as unknown as Record<string, string>).__auth_token = tok;
  } else {
    delete (window as unknown as Record<string, string>).__auth_token;
  }
}

const cache = new Map<string, CacheEntry>();
const CACHE_DURATION = 5 * 60 * 1000;

function getCachedKey(path: string, _options: RequestInit): string {
  return `${path}:${JSON.stringify(_options)}`;
}

function getFromCache(key: string): unknown | null {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.data;
  }
  cache.delete(key);
  return null;
}

function setCache(key: string, data: unknown): void {
  cache.set(key, { data, timestamp: Date.now() });
}

export async function authFetch<T = unknown>(path: string, options: AuthFetchOptions = {}, baseUrl?: string): Promise<T> {
  const headers: Record<string, string> = { ...options.headers };
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resolvedBase = baseUrl ?? API_BASE;

  if (options.method === undefined || options.method === 'GET') {
    const cacheKey = getCachedKey(`${resolvedBase}${path}`, options);
    const cachedData = getFromCache(cacheKey);
    if (cachedData) return cachedData as T;
  }

  const res = await fetch(`${resolvedBase}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }
  if (!res.ok) {
    let detail = '';
    try { const body = await res.json(); detail = body.detail || JSON.stringify(body); } catch {}
    const err = new Error(`${res.status}: ${detail || res.statusText}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  const data: T = await res.json();

  if ((options.method === undefined || options.method === 'GET') && res.ok) {
    const cacheKey = getCachedKey(`${resolvedBase}${path}`, options);
    setCache(cacheKey, data);
  }
  return data;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await authFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) setToken(data.access_token);
  return data;
}

export async function register(email: string, password: string, fullName: string): Promise<LoginResponse> {
  const data = await authFetch<LoginResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (data.access_token) setToken(data.access_token);
  return data;
}

export async function setPassword(password: string): Promise<void> {
  await authFetch('/auth/set-password', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function logout(): Promise<void> {
  try {
    await authFetch('/auth/logout', { method: 'POST' });
  } catch { /* ignore */ }
  setToken(null);
  window.dispatchEvent(new CustomEvent('auth:logout'));
}

export async function getMe(): Promise<LoginResponse> {
  return authFetch<LoginResponse>('/auth/me');
}

export async function isAuthenticated(): Promise<boolean> {
  try {
    const data = await getMe();
    return data.authenticated === true;
  } catch {
    return false;
  }
}

export async function getStats<T = unknown>(): Promise<T> {
  return authFetch<T>('/stats');
}

export async function getDistricts<T = unknown>(): Promise<T> {
  return authFetch<T>('/districts');
}

export async function getStates<T = unknown>(): Promise<T> {
  return authFetch<T>('/states');
}

export async function getBedForecast<T = unknown>({ state, ward_type, months_ahead, year }: BedForecastParams): Promise<T> {
  const params: Record<string, string> = { state, ward_type, months_ahead: String(months_ahead) };
  if (year) params.year = String(year);
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/predict/beds?${qs}`, { method: 'POST' });
}

export async function predictMortality<T = unknown>(params: Record<string, string>): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/predict/mortality?${qs}`, { method: 'POST' });
}

export async function getHospitalRankings<T>(params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const data = await authFetch<PaginatedResponse<T>>(`/hospitals/rankings?${qs}`);
  if (data && typeof data === 'object' && Array.isArray(data.results)) {
    (data.results as T & { _total?: number })._total = data.total;
    return data.results as T;
  }
  return data as T;
}

export async function getAdmissions<T = unknown>(params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/admissions?${qs}`);
}

export async function getLocationStats<T = unknown>(state?: string, district?: string): Promise<T> {
  const params: Record<string, string> = {};
  if (state) params.state = state;
  if (district) params.district = district;
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/locations/stats?${qs}`);
}

export async function getDistrictList<T = unknown>(state: string): Promise<T> {
  return authFetch<T>(`/locations/district-list?state=${encodeURIComponent(state)}`);
}

export async function getAllDistricts<T = unknown>(): Promise<T> {
  return authFetch<T>('/locations/districts/all');
}

export async function getHospitalDistribution<T = unknown>(): Promise<T> {
  return authFetch<T>('/hospitals/distribution');
}

export async function getLocalities<T = unknown>(district: string): Promise<T> {
  return authFetch<T>(`/locations/localities?district=${encodeURIComponent(district)}`);
}

export async function getPandemicScenario<T = unknown>(disease: string, state?: string, year?: string, manualR0?: number): Promise<T> {
  const params: Record<string, string> = { disease };
  if (state) params.state = state;
  if (year) params.year = year;
  if (manualR0 !== undefined) params.manual_r0 = String(manualR0);
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/pandemic/scenario?${qs}`);
}

export async function getPatients<T>(params: PatientListParams = {}): Promise<PaginatedResponse<T>> {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return authFetch<PaginatedResponse<T>>(`/patients?${qs}`, {}, PATIENT_API_BASE);
}

export async function getPatient<T = unknown>(id: number | string): Promise<T> {
  return authFetch<T>(`/patients/${id}`, {}, PATIENT_API_BASE);
}

export async function getPatientRisk<T = unknown>(patientId: number | string, virusName: string): Promise<T> {
  return authFetch<T>(`/patients/${patientId}/risk?virus_name=${encodeURIComponent(virusName)}`);
}

export async function getViruses<T = unknown>(): Promise<T> {
  return authFetch<T>('/patients/viruses/list', {}, PATIENT_API_BASE);
}

export async function getPatientStats<T = unknown>(): Promise<T> {
  return authFetch<T>('/patients/stats', {}, PATIENT_API_BASE);
}

export async function getSuggestions<T = unknown>(): Promise<T> {
  return authFetch<T>('/ai/suggestions');
}

export async function chatAI<T = unknown>(message: string, sessionId?: string, signal?: AbortSignal): Promise<T> {
  return authFetch<T>('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });
}

export async function globalSearch<T = unknown>(q: string, limit?: number): Promise<T> {
  const params: Record<string, string> = { q };
  if (limit) params.limit = String(limit);
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/search?${qs}`);
}

export function clearCache(): void {
  cache.clear();
}

export function clearCachePattern(pattern: string): void {
  for (const key of cache.keys()) {
    if (key.includes(pattern)) {
      cache.delete(key);
    }
  }
}
