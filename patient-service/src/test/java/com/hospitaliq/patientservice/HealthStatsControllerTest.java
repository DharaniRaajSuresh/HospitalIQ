package com.hospitaliq.patientservice;

import com.hospitaliq.patientservice.config.JwtAuthFilter;
import com.hospitaliq.patientservice.dto.HealthStatsResponse;
import com.hospitaliq.patientservice.service.HealthStatsService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Controller layer tests for {@link com.hospitaliq.patientservice.controller.HealthStatsController}.
 *
 * <p>Uses {@code @WebMvcTest} with security disabled to focus purely on:
 * <ul>
 *   <li>Route mapping ({@code GET /api/v1/health-stats})</li>
 *   <li>JSON serialisation of the {@link HealthStatsResponse} record</li>
 *   <li>HTTP status codes and content type</li>
 * </ul>
 */
@WebMvcTest(
    controllers = com.hospitaliq.patientservice.controller.HealthStatsController.class,
    excludeAutoConfiguration = {
        org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration.class,
        org.springframework.boot.autoconfigure.security.servlet.SecurityFilterAutoConfiguration.class
    },
    excludeFilters = @ComponentScan.Filter(
        type = FilterType.ASSIGNABLE_TYPE,
        classes = JwtAuthFilter.class
    )
)
class HealthStatsControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private HealthStatsService healthStatsService;

    // ------------------------------------------------------------------
    // GET /api/v1/health-stats
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/health-stats: returns 200 with all stat fields")
    void getHealthStats_returns200WithAllFields() throws Exception {
        HealthStatsResponse mockStats = new HealthStatsResponse(
                10_000L,
                2_340L,
                52.3,
                Map.of("A+", 3200L, "B+", 2800L, "O+", 2100L),
                "2026-06-01T12:00:00Z"
        );
        when(healthStatsService.getStats()).thenReturn(mockStats);

        mockMvc.perform(get("/api/v1/health-stats"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.total_patients").value(10_000))
                .andExpect(jsonPath("$.at_risk_count").value(2_340))
                .andExpect(jsonPath("$.avg_age").value(52.3))
                .andExpect(jsonPath("$.blood_group_distribution").isMap())
                .andExpect(jsonPath("$.cached_at").value("2026-06-01T12:00:00Z"));
    }

    @Test
    @DisplayName("GET /api/v1/health-stats: returns 200 with empty distribution when no patients")
    void getHealthStats_returnsEmptyDistributionWhenNoPatients() throws Exception {
        HealthStatsResponse emptyStats = new HealthStatsResponse(
                0L, 0L, 0.0, Map.of(), "2026-06-01T12:00:00Z"
        );
        when(healthStatsService.getStats()).thenReturn(emptyStats);

        mockMvc.perform(get("/api/v1/health-stats"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.total_patients").value(0))
                .andExpect(jsonPath("$.blood_group_distribution").isMap());
    }

    @Test
    @DisplayName("GET /api/v1/health-stats: returns JSON content-type header")
    void getHealthStats_returnsJsonContentType() throws Exception {
        when(healthStatsService.getStats()).thenReturn(
                new HealthStatsResponse(1L, 0L, 40.0, Map.of(), "2026-01-01T00:00:00Z")
        );

        mockMvc.perform(get("/api/v1/health-stats"))
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }
}
