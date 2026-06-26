package com.hospitaliq.patientservice;

import com.hospitaliq.patientservice.config.JwtAuthFilter;
import com.hospitaliq.patientservice.dto.PaginatedResponse;
import com.hospitaliq.patientservice.dto.PatientListResponse;
import com.hospitaliq.patientservice.dto.PatientStatsResponse;
import com.hospitaliq.patientservice.dto.VirusListResponse;
import com.hospitaliq.patientservice.service.PatientService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Controller layer tests using @WebMvcTest + MockMvc.
 * Security is fully excluded — JwtAuthFilter is excluded from the component scan,
 * and both security autoconfiguration classes are disabled.
 * This lets tests focus purely on MVC routing, parameter binding, and JSON serialization.
 */
@WebMvcTest(
    controllers = com.hospitaliq.patientservice.controller.PatientController.class,
    excludeAutoConfiguration = {
        org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration.class,
        org.springframework.boot.autoconfigure.security.servlet.SecurityFilterAutoConfiguration.class
    },
    excludeFilters = @ComponentScan.Filter(
        type = FilterType.ASSIGNABLE_TYPE,
        classes = JwtAuthFilter.class
    )
)
class PatientControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private PatientService patientService;

    // ------------------------------------------------------------------
    // GET /api/v1/patients
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients: returns 200 with paginated patient list")
    void listPatients_returns200() throws Exception {
        PatientListResponse patient = new PatientListResponse();
        // Use reflection-set via fromEntity — create a bare instance for test
        PaginatedResponse<PatientListResponse> page =
                new PaginatedResponse<>(List.of(patient), 1L, 0, 20);

        when(patientService.listPatients(any(), any(), anyInt(), anyInt()))
                .thenReturn(page);

        mockMvc.perform(get("/api/v1/patients").param("limit", "20").param("offset", "0"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.total").value(1))
                .andExpect(jsonPath("$.patients").isArray());
    }

    @Test
    @DisplayName("GET /api/v1/patients: accepts 'offset' param as alias for 'skip'")
    void listPatients_supportsOffsetParam() throws Exception {
        PaginatedResponse<PatientListResponse> page =
                new PaginatedResponse<>(List.of(), 0L, 20, 20);

        when(patientService.listPatients(isNull(), isNull(), eq(20), eq(20)))
                .thenReturn(page);

        mockMvc.perform(get("/api/v1/patients").param("limit", "20").param("offset", "20"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.skip").value(20));
    }

    // ------------------------------------------------------------------
    // GET /api/v1/patients/{id}
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients/{id}: returns 404 for unknown patient")
    void getPatient_notFound_returns404() throws Exception {
        when(patientService.getPatientDetail(999))
                .thenThrow(new com.hospitaliq.patientservice.exception.PatientNotFoundException(999));

        mockMvc.perform(get("/api/v1/patients/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("Patient not found"));
    }

    @Test
    @DisplayName("GET /api/v1/patients/{id}: returns 422 for non-integer ID")
    void getPatient_invalidId_returns422() throws Exception {
        mockMvc.perform(get("/api/v1/patients/abc"))
                .andExpect(status().isUnprocessableEntity());
    }

    // ------------------------------------------------------------------
    // GET /api/v1/patients/viruses/list
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients/viruses/list: returns 200 with virus list")
    void listViruses_returns200() throws Exception {
        VirusListResponse virusResponse = new VirusListResponse(List.of());
        when(patientService.listViruses()).thenReturn(virusResponse);

        mockMvc.perform(get("/api/v1/patients/viruses/list"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.viruses").isArray());
    }

    // ------------------------------------------------------------------
    // GET /api/v1/patients/stats
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/v1/patients/stats: returns 200 with all stat fields")
    void getStats_returns200WithAllFields() throws Exception {
        PatientStatsResponse stats = new PatientStatsResponse(
                10000L, 52.3, 2340L, Map.of("A+", 3200L, "B+", 2800L));
        when(patientService.getPatientStats()).thenReturn(stats);

        mockMvc.perform(get("/api/v1/patients/stats"))
                .andExpect(status().isOk())
                // Jackson SNAKE_CASE strategy converts camelCase getter names to snake_case in JSON
                .andExpect(jsonPath("$.total_patients").value(10000))
                .andExpect(jsonPath("$.avg_age").value(52.3))
                .andExpect(jsonPath("$.at_risk_count").value(2340))
                .andExpect(jsonPath("$.blood_group_distribution").isMap());
    }
}
