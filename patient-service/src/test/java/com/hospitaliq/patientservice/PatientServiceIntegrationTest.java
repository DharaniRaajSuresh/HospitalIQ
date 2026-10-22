package com.hospitaliq.patientservice;

import com.hospitaliq.patientservice.entity.PatientEntity;
import com.hospitaliq.patientservice.repository.PatientRepository;
import com.hospitaliq.patientservice.service.HealthStatsService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Full integration tests for the Patient Service — loads the complete Spring application context.
 *
 * <p>Unlike {@link PatientControllerTest} ({@code @WebMvcTest}, service mocked) and
 * {@link PatientRepositoryTest} ({@code @DataJpaTest}, no web layer), this class exercises
 * the <strong>entire stack</strong>:
 * <pre>
 *   HTTP request → DispatcherServlet → JwtAuthFilter → SecurityFilterChain
 *     → PatientController → PatientService → PatientRepository → H2 in-memory DB
 * </pre>
 *
 * <p>Uses {@code WebEnvironment.MOCK} (not {@code RANDOM_PORT}) so that MockMvc and
 * the test method share the same thread — this allows {@code @Transactional} to propagate
 * the test-scoped database state to the controller layer without starting a real HTTP server.
 *
 * <p>H2 in-memory DB is configured via {@code src/test/resources/application-test.yml}.
 *
 * <p>Tests verify:
 * <ol>
 *   <li>Protected endpoints return {@code 401 Unauthorized} without a JWT token
 *       (JwtAuthFilter + SecurityConfig both active — impossible to test with {@code @WebMvcTest})</li>
 *   <li>Public endpoints return {@code 200 OK} without authentication</li>
 *   <li>The full {@code Controller → Service → Repository → DB} chain produces correct JSON</li>
 *   <li>The {@code /health-stats} endpoint returns fresh aggregate data after cache refresh</li>
 * </ol>
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class PatientServiceIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private PatientRepository patientRepository;

    @Autowired
    private HealthStatsService healthStatsService;

    // ------------------------------------------------------------------
    // Test data setup — runs within the same @Transactional as each test
    // ------------------------------------------------------------------

    @BeforeEach
    void setUp() {
        PatientEntity p1 = new PatientEntity();
        p1.setPatientName("Arjun Mehta");
        p1.setAge(45);
        p1.setBloodGroup("O+");
        p1.setGender("Male");
        p1.setState("Maharashtra");
        p1.setPreExistingConditions("Diabetes");
        patientRepository.save(p1);

        PatientEntity p2 = new PatientEntity();
        p2.setPatientName("Priya Singh");
        p2.setAge(30);
        p2.setBloodGroup("A+");
        p2.setGender("Female");
        p2.setState("Delhi");
        p2.setPreExistingConditions(null);
        patientRepository.save(p2);

        patientRepository.flush();

        // Force HealthStatsService to recompute from DB after data is seeded.
        // Necessary because the AtomicReference cache may hold a stale (empty) snapshot
        // from before @BeforeEach ran. refreshCache() is idempotent and thread-safe.
        healthStatsService.refreshCache();
    }

    // ------------------------------------------------------------------
    // Authentication boundary tests
    // Only possible with @SpringBootTest — JwtAuthFilter is fully active here,
    // unlike @WebMvcTest where security auto-configuration is excluded.
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients — returns 401 Unauthorized without JWT token")
    void listPatients_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/v1/patients"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/v1/patients/{id} — returns 401 Unauthorized without JWT token")
    void getPatient_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/v1/patients/1"))
                .andExpect(status().isUnauthorized());
    }

    // ------------------------------------------------------------------
    // Public endpoint tests — no auth required
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients/viruses/list — returns 200 OK without auth (public endpoint)")
    void listViruses_withoutToken_returns200() throws Exception {
        mockMvc.perform(get("/api/v1/patients/viruses/list"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.viruses").isArray());
    }

    @Test
    @DisplayName("GET /api/v1/patients/stats — returns 200 OK without auth (public endpoint)")
    void patientStats_withoutToken_returns200() throws Exception {
        mockMvc.perform(get("/api/v1/patients/stats"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.total_patients").isNumber())
                .andExpect(jsonPath("$.avg_age").isNumber())
                .andExpect(jsonPath("$.at_risk_count").isNumber());
    }

    // ------------------------------------------------------------------
    // Full-stack data tests — Controller → Service → Repository → H2 DB
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients/stats — total_patients reflects seeded data")
    void patientStats_returnsSeededCount() throws Exception {
        mockMvc.perform(get("/api/v1/patients/stats"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.total_patients").value(greaterThanOrEqualTo(2)));
    }

    @Test
    @DisplayName("GET /api/v1/health-stats — returns 200 with aggregate data from real DB")
    void healthStats_returnsAggregateFromDb() throws Exception {
        mockMvc.perform(get("/api/v1/health-stats"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.total_patients").value(greaterThanOrEqualTo(2)))
                .andExpect(jsonPath("$.avg_age").isNumber())
                .andExpect(jsonPath("$.at_risk_count").isNumber())
                .andExpect(jsonPath("$.cached_at").isString());
    }
}
