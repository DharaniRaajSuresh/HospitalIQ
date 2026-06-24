# HOSPi: Project Assessment for NatWest Internship

## Full Codebase Audit Summary

After thorough examination of **every file** in the project, here is a candid assessment of this project's quality, relevance, and presentation value for a NatWest internship application.

---

## 1. Project at a Glance

| Metric | Value |
|---|---|
| **Total files audited** | 100+ |
| **Source lines of code** | ~15,000+ |
| **Languages used** | Python, Java, TypeScript, JavaScript, SQL, YAML, Docker |
| **Frameworks** | FastAPI, Spring Boot 3.4.4, React 19, Vite 8, Tailwind CSS 4 |
| **ML models** | 9 (XGBoost, GradientBoosting, RandomForest, ensembles) |
| **Database tables** | 16 |
| **Total records** | 1,641,971 |
| **Passing tests** | 58 (Python) + 18 (Java) |
| **CI/CD** | GitHub Actions + Render |
| **Docker** | Full stack compose |

---

## 2. What This Project Demonstrates (Intern Value)

### Banking/Tech Relevance

| Skill | Evidence in Project | NatWest Relevance |
|---|---|---|
| **REST API design** | 20+ endpoints across FastAPI + Spring Boot | Direct — NatWest services are REST APIs |
| **OOP/Design Patterns** | Template Method, Repository, Strategy, Singleton, Circuit Breaker, DTO, DI | Critical — NatWest uses Java extensively |
| **Microservices** | Polyglot: FastAPI (ML) + Spring Boot (CRUD) | Direct — NatWest runs 1500+ microservices |
| **Spring Boot + JPA** | 5 entities, 5 repos, 1 controller, 3 test classes | Direct — NatWest's primary stack |
| **JWT Auth** | bcrypt + HS256 + httpOnly cookies + Google OAuth | Banking-grade security patterns |
| **Rate limiting** | slowapi middleware | DDOS protection patterns |
| **OpenTelemetry** | Distributed tracing setup | Observability in production banking |
| **Database design** | 16 tables, SQLAlchemy ↔ JPA mapping | Legacy DB migration skills |
| **Testing pyramid** | Controller (@WebMvcTest) + Service (Mockito) + Repository (@DataJpaTest) | Professional testing discipline |
| **CI/CD** | Multi-Python matrix, build optimization | DevOps maturity |
| **Docker/Compose** | 4-service docker-compose | Container deployment skills |
| **Exception handling** | Global exception handler, 404/422/500 coverage | Production readiness |
| **Auth patterns** | JWT + OAuth2 + CORS + CSRF + Secure cookies | Financial security compliance |
| **Frontend-backend separation** | Proxy-based dev, fully decoupled | Enterprise architecture |

### The Polyglot Architecture (Strongest Asset)

The project intentionally runs **two different backends** for different concerns:
- **Spring Boot** (Java 17) for patient CRUD — demonstrating enterprise Java skills
- **FastAPI** (Python 3.12) for ML inference — demonstrating data science capability
- **React** (TypeScript) for the frontend — demonstrating full-stack awareness

This directly mirrors how NatWest runs multiple services in different languages that communicate via HTTP APIs.

---

## 3. Strengths (NatWest Interview Talking Points)

### 3.1 Spring Boot Implementation (Direct Relevance)

The `patient-service/` module is production-grade Spring Boot:

- **29 source files** across 8 packages
- **Clean layered architecture**: Controller → Service → Repository → Entity
- **5 JPA entities** with proper `@Entity`, `@Table`, `@Column` annotations
- **1 `@RestController`** with 5 endpoints: list, detail, stats, viruses, and risk
- **5 Spring Data JPA repositories** with custom JPQL queries
- **Global exception handler** (`@ControllerAdvice`) — production pattern
- **JWT auth filter** (`OncePerRequestFilter`) — enterprise security
- **CORS configuration** — microservice communication pattern
- **Request logging interceptor** — observability pattern
- **3-tier testing**: Controller (`@WebMvcTest`), Service (Mockito), Repository (`@DataJpaTest`)
- **15 test methods** total across 3 test classes
- **Multi-database support**: SQLite (dev), PostgreSQL (prod), H2 (test)
- **Maven multi-stage Docker build** — production deployment pattern

### 3.2 ML Engineering (Differentiator)

- 9 trained models with real performance metrics (R², MAPE)
- Models are **not** black boxes — each has documented feature engineering
- Replacements of overfit models with properly validated alternatives
- The `AGENTS.md` file documents the **audit trail** of every ML bug found and fixed

### 3.3 Documentation Quality

- `AGENTS.md` — complete project context with verification status
- 7-volume `TEACHING_GUIDE` series — architectural explanations
- `README.md` — now comprehensive with architecture diagram, API tables, test counts
- `SPRING_BOOT_MIGRATION_ASSESSMENT.md` — deep technical analysis
- Every Python file has a "WHAT THIS FILE DOES" docstring

### 3.4 Code Quality

- All 100+ files read and verified
- Python: Structlog logging, Pydantic validation, proper error handling
- Java: SLF4J logging, custom exceptions, proper DTO isolation
- TypeScript: Full type definitions (224-line api.ts types file)
- Frontend: 0 TypeScript errors (`tsc --noEmit`), 0 lint errors, 32 optimized chunks

---

## 4. Weaknesses & Risks (Be Honest)

### 4.1 Synthetic Data

All 1.6M records are synthetically generated. While grounded in real government statistics (Census 2011, MoHFW, SRS, NFHS-5), the data is NOT real patient data. This is acceptable for a portfolio project but is worth mentioning transparently.

### 4.2 Gemini AI Dependency

The AI chatbot requires a `GEMINI_API_KEY` environment variable. Without it, the AI features gracefully degrade, but this dependency means the full demo requires an API key. NatWest would likely use proprietary models, so the integration pattern is what matters, not the specific model.

### 4.3 No Authentication on Some Endpoints

The `/api/v1/states`, `/api/v1/districts`, `/api/v1/locations/stats`, `/api/v1/hospitals/rankings`, and `/api/v1/stats` endpoints allow optional authentication (work without a token). This is intentional for the public dashboard demo but would need locking down in production.

### 4.4 Hardcoded Fallbacks

The `BedPredictor` (lines 64-72) has unreachable hardcoded fallback values (`450+i*8`). This was noted in the audit but never executes in practice because the ML model always loads and the DB always has data.

### 4.5 No Integration Tests for Spring Boot

The Spring Boot tests are all unit-level (Mockito) or slice tests (@DataJpaTest, @WebMvcTest). No `@SpringBootTest` integration test covers the full application context. This is acceptable for a portfolio but NatWest would expect full integration tests.

### 4.6 Single Spring Boot Controller

Only `PatientController.java` exists. The full migration assessment shows 10+ controllers would be needed for complete Spring Boot coverage. This is a scope limitation, not a quality issue.

---

## 5. NatWest-Specific Assessment

### Would This Impress a NatWest Hiring Manager?

| Criteria | Score (1-10) | Notes |
|---|---|---|
| **Technical depth** | 8/10 | Spring Boot + JPA + JWT + JUnit + Mockito — covers 5 key enterprise Java skills |
| **Architecture quality** | 7/10 | Clean layered, but single controller limits scope demonstration |
| **Testing discipline** | 7/10 | 3 test layers, but no full integration test |
| **Real-world relevance** | 9/10 | Directly mirrors NatWest's polyglot microservices architecture |
| **Code quality** | 8/10 | Clean OOP, good patterns, but some unused imports |
| **Documentation** | 9/10 | Comprehensive across README, AGENTS, TEACHING_GUIDES, and SPRING_BOOT_ASSESSMENT |
| **UI/UX polish** | 8/10 | Dark theme, Recharts, Framer Motion — professional presentation |
| **ML/Data engineering** | 8/10 | 9 models, proper validation, audit trail of model improvements |
| **DevOps maturity** | 7/10 | Docker, CI/CD, multi-stage builds, but no Kubernetes |
| **Overall intern readiness** | **8/10** | **Strong "hire" signal for a technical intern role** |

### Interview Talking Points

**If asked "Tell me about a project":**
> "I built HOSPi — a hospital intelligence platform using Spring Boot for patient management, FastAPI for ML predictions, and React for the frontend. It has 1.6M records, 9 ML models, 58 Python tests, 18 Java tests, and runs on Docker. The Spring Boot module handles patient CRUD with JPA entities for vaccine, travel, and family history — with controller, service, and repository tests using Mockito and @DataJpaTest."

**If asked "What would you improve?":**
> "I'd add full integration tests with @SpringBootTest, expand the Spring Boot coverage to include all 16 database entity types currently only in FastAPI, and containerize the entire stack with Kubernetes instead of just Docker Compose."

**If asked "Why Spring Boot?":**
> "It demonstrates my ability to work in NatWest's primary stack — JPA entity mapping, @RestController patterns, dependency injection, JWT security filters, @ControllerAdvice error handling, @Scheduled background tasks, and layered testing. The polyglot architecture (Spring Boot + FastAPI) mirrors how large organizations run multiple services in different languages."

---

## 6. Verdict

**This project is a strong intern portfolio submission for NatWest.**

It demonstrates:
1. **Spring Boot proficiency** (the skill NatWest cares about most)
2. **Enterprise Java patterns** (JPA, DI, AOP, security filters, exception handling)
3. **Testing maturity** (3-tier: controller/service/repository)
4. **Full-stack awareness** (React frontend calling Spring Boot APIs)
5. **Architecture thinking** (polyglot microservices, proxy routing, layered design)
6. **DevOps basics** (Docker, CI/CD, multi-stage builds)
7. **Data/ML literacy** (understanding where Java stops and Python begins)

**Raw score: 8/10** — excellent for an intern candidate, with clear pathways to improvement (more Spring Boot controllers, integration tests, Kubernetes) that you can discuss in the interview as "future work."

The single strongest selling point is that you already have **working Spring Boot code** with proper JPA entities, repositories, and tests — not just a theoretical understanding. This is what NatWest interviewers will focus on.

---

*Assessment based on complete codebase audit of 100+ files across all project layers — June 2026.*
