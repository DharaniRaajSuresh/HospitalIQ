# HOSPi Teaching Guide — Volume 2: Frontend Layer

> **Depth Level:** Source code walkthrough with production-grade analysis. Every file, every pattern, every tradeoff explained.

---

## 1. `api.ts` — THE FAANG-GRADE API CLIENT

**File:** `frontend/src/api.ts` (165 lines)

### 1.1 What It Does

This is the **single file through which ALL frontend-to-backend communication flows**. It's not just a fetch wrapper — it's a complete API client with:

- JWT token management (read from/write to `window.__auth_token`)
- Automatic Bearer header injection
- GET request caching (5-minute TTL in `Map<string, CacheEntry>`)
- Auth error detection (401 → dispatches `auth:logout` custom event)
- Typed generic responses (`authFetch<T>`)
- 18 named endpoint functions covering every API route

### 1.2 Why It Was Written This Way

**Problem it solves:** Before this file existed, each React component used raw `fetch()` with duplicated auth logic, token management, and error handling. This caused 401 errors on 7 pages, inconsistent caching, and hard-to-debug network failures.

**Architectural decision:** Instead of using a heavyweight library like React Query or Redux Toolkit Query, the author chose a **lightweight custom client** because:
- The project has only 18 endpoints — not enough to justify a full query library
- The caching logic is simple (5-min TTL, GET-only, in-memory Map)
- Custom error handling (401 → auto-logout) is application-specific
- Zero additional bundle size

**Tradeoff:** No request deduplication, no stale-while-revalidate, no optimistic updates. If the app grows to 50+ endpoints, React Query would be a better choice.

### 1.3 Code Walkthrough — Line by Line

```typescript
interface CacheEntry {
  data: unknown;
  timestamp: number;
}
```
**Why `unknown` instead of `T`?** The cache stores the raw parsed JSON before type assertion happens at the call site. The type parameter `T` in `authFetch<T>` is applied AFTER cache retrieval. Using `unknown` forces the caller to handle the type, which is correct here — the cache doesn't know about types.

```typescript
const API_BASE = '/api/v1';
```
**Why no config?** In development, the Vite proxy at `vite.config.js:20` forwards `/api` to `localhost:8000`. In production, nginx does the same. The frontend never needs to know the backend URL — a good **separation of concerns**.

```typescript
function getToken(): string | null {
  return (typeof window !== 'undefined' && (window as unknown as Record<string, string>).__auth_token) || null;
}
```
**Why store token on `window`?** This is a controversial design choice. Normally tokens are stored in httpOnly cookies (which is what the backend does for cookie auth) or localStorage. Here, the token needs to be accessible to JavaScript so the `Authorization: Bearer` header can be set. 

**Security concern:** Storing the JWT in a JavaScript-accessible global (`window.__auth_token`) makes it vulnerable to XSS attacks. A better approach would be to rely entirely on the httpOnly cookie (which the backend sets via `set_token_cookie()`) and let the browser send it automatically. But the frontend code sends an explicit `Authorization` header as well.

**Why both cookie AND header?** The backend's `_extract_token()` (in `auth.py:73-78`) checks the Authorization header first, then falls back to the cookie. The frontend sends both — the explicit header for API clients/Postman, the cookie for browser-native requests. This is a **dual-auth strategy**.

```typescript
const cache = new Map<string, CacheEntry>();
const CACHE_DURATION = 5 * 60 * 1000;  // 5 minutes
```
**Why Map instead of object?** `Map` has better performance for frequent get/set/delete operations and provides `.keys()`, `.entries()`, and `.delete()` methods needed by `clearCachePattern()`.

```typescript
function getCachedKey(path: string, _options: RequestInit): string {
  return `${path}:${JSON.stringify(_options)}`;
}
```
**Why include options in the key?** Different request headers (e.g., different Content-Type) should produce different cache entries. Including the full options object as JSON means the cache is sensitive to header changes.

**Bug potential:** `_options` could contain non-serializable values (like `AbortSignal` or `FormData`). The underscore prefix suggests the author knows this is fragile. In practice, GET requests have minimal options so it works.

```typescript
if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:logout'));
}
```
**Why a custom event instead of redirecting directly?** Decoupling. The `auth:logout` event is listened to by... nothing in the current code. But it was designed to be hooked into by a global auth manager. Currently, `logout()` in `api.ts` also dispatches this event but nothing handles it.

**Missing implementation:** There should be a `useEffect` in `App.tsx` that listens for this event and redirects to `/`. Without it, a 401 response dispatches an event that nobody handles.

```typescript
export async function getHospitalRankings<T>(params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const data = await authFetch<PaginatedResponse<T>>(`/hospitals/rankings?${qs}`);
  if (data && typeof data === 'object' && Array.isArray(data.results)) {
    (data.results as T & { _total?: number })._total = data.total;
    return data.results as T;
  }
  return data as T;
}
```
**Why unwrap `results`?** The backend returns `{"total": 1000, "results": [...]}` but the frontend ranking component expects an array. This function extracts `results` and attaches `_total` as a hidden property. It's a **workaround** for an API design mismatch — the endpoint returns a paginated wrapper but the component expects a flat array.

### 1.4 What Would Break If Removed

If `api.ts` were deleted:
- Every page would need to reimplement `fetch()`, token management, error handling, and caching
- 7 pages would immediately 401 (they were using raw fetch before the fix)
- No centralized place to handle 401 → auto-logout
- No caching: every page component mount would re-fetch the same data

### 1.5 Performance Analysis

- **Cache hit time:** O(1) Map lookup + timestamp comparison
- **Serialization overhead:** `JSON.stringify(options)` on every request for cache key generation — negligible for simple GET requests
- **Memory:** Worst case, 5 minutes of unique GET requests cached. At ~1KB per entry (typical API response), ~1.2MB max with one request per second
- **Cache invalidation:** Time-based only (5-min TTL). No mutation-based invalidation. If a user adds a patient, the patient list cache isn't cleared — they'd need to wait 5 minutes or the page would show stale data

---

## 2. `App.tsx` — ROUTING, AUTH STATE, AND LAZY LOADING

**File:** `frontend/src/App.tsx` (105 lines)

### 2.1 What It Does

This is the **React application root** component. It:

1. On mount, checks if the user is already authenticated via `isAuthenticated()`
2. If not authenticated and demo credentials exist in env vars, auto-logs in
3. Shows a loading screen for 5 seconds (or until auth check completes)
4. Renders the router with lazy-loaded pages
5. Wraps everything in `AmbientBackground` (particle effects)

### 2.2 Why This Architecture

**Problem:** The app needs to check auth state BEFORE rendering any protected routes. But the auth check is async (HTTP call to `/auth/me`). The solution is the **`isReady` state variable** — a boolean gate that starts `false` and becomes `true` only after auth check completes (or 5-second timeout elapses).

**Why 5-second timeout?** If the backend is slow to respond, the user shouldn't see a loading spinner forever. The timeout at line 24 (`setTimeout(() => { if (mounted) setIsReady(true); }, 5000)`) ensures the app loads even if auth fails silently.

**Race condition handling:** The `mounted` boolean flag and `clearTimeout` in the cleanup function prevent:
- State updates after component unmount
- Double auth checks
- Memory leaks from orphaned timeouts

### 2.3 Code Walkthrough

```typescript
const timeout = setTimeout(() => { if (mounted) setIsReady(true); }, 5000);
```
**This is a failsafe.** If the auth check hangs (backend down, network issue), the app still loads after 5 seconds. Without this, the user would see a loading spinner forever.

```typescript
async function checkAndLogin(): Promise<void> {
    const authed = await isAuthenticated();
    if (!authed && mounted && import.meta.env.VITE_DEMO_EMAIL && import.meta.env.VITE_DEMO_PASSWORD) {
        await login(import.meta.env.VITE_DEMO_EMAIL as string, import.meta.env.VITE_DEMO_PASSWORD as string);
    }
}
```
**Why env var credentials?** Previously, demo credentials were hardcoded in `App.tsx` — a security risk. The fix was to move them to environment variables. If `VITE_DEMO_EMAIL` and `VITE_DEMO_PASSWORD` are not set (production deployment), the auto-login is skipped entirely.

```typescript
const LandingPage = lazy(() => import('./pages/LandingPage'));
```
**Why `lazy()`?** Code splitting. The landing page (with heavy animations: GSAP, Lenis scroll, particle effects) is loaded only when the user visits `/`. Without lazy loading, the initial bundle would include all 12 pages + FloatingCopilot + all their dependencies.

**How it works:** Vite detects `import()` and creates a separate chunk. When the user navigates to a lazy route, React Suspense shows the `PageLoader` fallback while the chunk loads. This is visible as a brief loading spinner between page navigations.

```typescript
<Suspense fallback={<PageLoader />}>
    <AnimatePresence mode="wait">
        <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dashboard" element={<DashboardLayout />}>
                <Route index element={<CommandCenter />} />
                <Route path="beds" element={<BedForecast />} />
                ...
            </Route>
        </Routes>
    </AnimatePresence>
</Suspense>
```
**Why `AnimatePresence`?** Framer Motion's `AnimatePresence` enables exit animations when routes change. The `mode="wait"` ensures the exit animation of the current route completes before the enter animation of the next route starts — preventing visual glitches.

**Why nested routes under `/dashboard`?** The `DashboardLayout` component provides the sidebar navigation, header, and consistent layout for all dashboard pages. The `<Outlet />` in DashboardLayout renders the child route. This avoids duplicating layout code in every page.

### 2.4 What Would Break If Removed

- No auth check: users would see empty dashboards or 401 errors
- No lazy loading: initial bundle would be ~500KB instead of ~50KB
- No PageLoader: blank screen while chunks load
- No AmbientBackground: the signature cyberpunk particle effect disappears

---

## 3. `vite.config.js` — THE BUILD PIPELINE

**File:** `frontend/vite.config.js` (38 lines)

### 3.1 What It Does

Configures Vite 8 with:
- React plugin (JSX transform)
- Tailwind CSS v4 integration
- Pre-bundling of heavy dependencies (`jspdf`, `recharts`, `leaflet`, `react-leaflet`)
- Manual chunk splitting into 6 vendor groups
- Dev server proxy (port 8510 → backend port 8000)
- Vitest configuration (JSDOM environment)

### 3.2 Chunk Split Strategy

```javascript
manualChunks(id) {
  if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/react-router-dom'))
    return 'react-vendor';
  if (id.includes('node_modules/framer-motion') || id.includes('node_modules/lucide-react'))
    return 'ui-vendor';
  if (id.includes('node_modules/recharts'))
    return 'charts-vendor';
  if (id.includes('node_modules/leaflet') || id.includes('node_modules/react-leaflet'))
    return 'maps-vendor';
  if (id.includes('node_modules/clsx') || id.includes('node_modules/tailwind-merge'))
    return 'utils-vendor';
}
```

**Why this matters:** Without manual chunks, Vite might split code in unpredictable ways, creating many tiny chunks (bad for HTTP/1.1) or one giant vendor chunk (bad for caching). The strategy here:

- **React vendor** (react, react-dom, react-router-dom) — Changes rarely, cacheable for months
- **UI vendor** (framer-motion, lucide-react) — Animation/glyph libraries
- **Charts vendor** (recharts) — Heavy charting library, only needed on analytics pages
- **Maps vendor** (leaflet, react-leaflet) — Only needed on map pages
- **Utils vendor** (clsx, tailwind-merge) — Small utility libraries

The Vite 8 upgrade required switching from object syntax (`manualChunks: { ... }`) to function syntax (`manualChunks(id) { ... }`) — a breaking change from Vite 7.

---

## 4. `tsconfig.json` — STRICT-LITE TYPE CONFIG

**File:** `frontend/tsconfig.json` (26 lines)

### 4.1 The Strategy

The TypeScript config uses a **"strict-lite"** approach:
- `strict: false` — base strict mode OFF
- `strictFunctionTypes: true` — function parameter contravariance checked
- `strictBindCallApply: true` — `.bind()/.call()/.apply()` arguments checked
- `noImplicitAny: false` — allows implicit `any` (the escape hatch)
- `skipLibCheck: true` — skips type checking of `.d.ts` files (fast compilation)

**Why not full strict?** The project was converted from JSX to TSX in a single batch (35 files). Full strict mode would produce 640+ errors from `useState([])` — without a type parameter, `useState([])` infers `never[]` in strict mode. Fixing all these errors would be days of work.

**The pragmatic decision:** Use enough strict checks to catch real bugs (`strictFunctionTypes`, `strictBindCallApply`) while allowing implicit `any` to avoid the 640+ spurious errors. The 18 `@ts-nocheck` files are a further concession — files with too many errors to fix immediately.

**How to progress:** Remove `@ts-nocheck` from one file at a time, fix the actual type errors, then eventually set `noImplicitAny: true` and finally `strict: true`.

---

## 5. COMPONENT DEEP-DIVE: ForecastingCenter.tsx

**File:** `frontend/src/pages/ForecastingCenter.tsx` (246 lines)

### 5.1 State Management

```typescript
const [rawForecast, setRawForecast] = useState(null);
const [state, setState] = useState('');
const [wardType, setWardType] = useState('ICU');
const [monthsAhead, setMonthsAhead] = useState(12);
const [selectedYear, setSelectedYear] = useState(CURRENT_YEAR);
const [pandemicMode, setPandemicMode] = useState(false);
const [surgePct, setSurgePct] = useState(50);
const [severityPct, setSeverityPct] = useState(30);
```

**Why so many useState hooks?** Each one controls a form parameter. The pandemic mode toggle adds surge/mortality severity sliders. Every parameter change triggers `handleRunSimulation()` which re-fetches from the API.

**Redundancy note:** `monthsAhead` and `selectedYear` are somewhat redundant — changing the year recalculates months ahead. The `handleYearChange` function at line ~72:
```typescript
const needed = Math.max(12, (year - CURRENT_YEAR) * 12 + 12);
setMonthsAhead(needed);
handleRunSimulation(needed, year);
```
This ensures enough months are requested to cover the selected year.

### 5.2 Chart Rendering

The chart at the bottom uses `Recharts`'s `ComposedChart` with:
- **Area** for confidence intervals (upper/lower bounds)
- **Bar** for historical demand
- **Line** for AI-predicted demand (dashed, with neon glow SVG filter)

**Why ComposedChart instead of separate components?** A composed chart lets you overlay bar + line + area on the same axis, showing historical data, predictions, and confidence intervals in a single visualization. This is the expected format for financial/forecasting dashboards.

**SVG filters for neon glow:**
```jsx
<filter id="neonGlow">
    <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="var(--color-accent-violet)" />
    <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor="var(--color-accent-violet)" />
</filter>
```
This creates a double-drop-shadow effect that simulates a neon glow on the prediction line. It's a CSS/ SVG trick, not a custom renderer — performant because it's GPU-accelerated.

### 5.3 Loading State

```jsx
{loading && (
    <div className="absolute inset-0 z-10 bg-[var(--color-bg-card)]/50 backdrop-blur-sm flex items-center justify-center rounded-xl">
        <div className="w-10 h-10 border-4 border-[var(--color-accent-violet)] border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-[var(--color-accent-violet)] font-medium animate-pulse">Running ML Prediction...</p>
    </div>
)}
```

**Why overlay instead of replacing content?** An overlay keeps the chart in the DOM (preventing layout shift when loading completes) while visually blocking interaction. The `backdrop-blur-sm` provides a glass-morphism effect consistent with the design system.

---

## 6. PANDEMIC MODE — CLIENT-SIDE SIMULATION

In `ForecastingCenter.tsx`, pandemic mode is purely **client-side**:

```typescript
const surgeFactor = pandemicMode ? 1 + (surgePct / 100) : 1;
const mapped = forecast.map((f, i) => ({
    predicted: Math.round((f.predicted_beds || 0) * surgeFactor),
    lower: Math.round((f.predicted_beds || 0) * (pandemicMode ? surgeFactor * 0.85 : 0.8)),
    upper: Math.round((f.predicted_beds || 0) * (pandemicMode ? surgeFactor * 1.15 : 1.2)),
}));
```

**What it does:** Takes the ML-predicted bed forecast and multiplies by a surge factor (1.0-3.0). The confidence intervals widen proportionally. The backend never knows about pandemic mode — it's entirely a frontend visualization trick.

**Why not send pandemic params to backend?** The backend's `BedPredictor` was trained on historical data without pandemic scenarios. Adding surge scaling to the backend would require: (a) retraining with pandemic data, (b) adding a `surge_factor` parameter to the model, or (c) post-processing the prediction. The frontend approach avoids backend changes but means the surge-scaled numbers don't come from the ML model — they're just math.

**Interview answer:** "The pandemic mode is a client-side multiplier applied to ML predictions. It demonstrates the forecasting tool's flexibility but the surge-adjusted numbers aren't ML-derived. A production version would use a separate pandemic surge model trained on historical outbreak data."

---

## 7. ARCHITECTURAL PATTERNS IN THE FRONTEND

### 7.1 Custom Hooks vs. Classes

The frontend uses zero custom hooks (besides `useState`/`useEffect`). All API calls are made directly in `useEffect` blocks. This works for 12 pages but leads to duplicated code (loading/error state management in every component).

**Better approach:** Create a `useApi` hook:
```typescript
function useApi<T>(fetcher: () => Promise<T>, deps: any[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetcher().then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, deps);
  return { data, loading, error };
}
```

### 7.2 State Management

The app uses **React's built-in state management** (useState + props) with no Redux, Zustand, or Context API. For this scope (12 pages, no deeply nested state), it's appropriate. The tradeoff:
- **Pro:** Zero dependencies, simple mental model, fast renders
- **Con:** Props drilling if pages get nested components; no devtools for state inspection

### 7.3 CSS Architecture

Tailwind CSS v4 with CSS custom properties (variables):
```css
--color-accent-cyan: #00f0ff;
--color-accent-violet: #b026ff;
--color-bg-card: rgba(15, 23, 42, 0.4);
```

**Why CSS variables instead of Tailwind's `theme.extend`?** CSS variables can be changed at runtime (e.g., theme switching). They're also accessible in SVG filters (used in chart defs) where Tailwind classes don't work.

---

## 8. FRONTEND PERFORMANCE

The `npm run build` produces 32 chunks totaling ~1.2MB (gzipped ~350KB):

| Chunk | Size | Contents |
|---|---|---|
| `react-vendor-*.js` | ~50KB | React 19, ReactDOM, React Router |
| `ui-vendor-*.js` | ~70KB | Framer Motion, Lucide Icons |
| `charts-vendor-*.js` | ~120KB | Recharts |
| `maps-vendor-*.js` | ~180KB | Leaflet, React Leaflet |
| `index-*.js` | ~8KB | App.tsx + Router |
| `CommandCenter-*.js` | ~15KB | Dashboard page |
| `ForecastingCenter-*.js` | ~12KB | Bed forecast page |
| `LandingPage-*.js` | ~50KB | Landing page (heavy animations) |

**What the chunk strategy achieves:**
- **Cache efficiency:** React vendor chunk changes rarely — users download it once across deployments
- **Parallel loading:** Maps vendor and charts vendor are lazy-loaded only when needed
- **Code splitting:** Each page loads independently — visiting Bed Forecast doesn't download the AI Chatbot code

---

*End of Volume 2. Continue to Volume 3 for the Backend Layer deep-dive.*
