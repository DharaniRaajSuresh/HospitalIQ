package com.hospitaliq.patientservice.controller;

import com.hospitaliq.patientservice.constants.AppConstants;
import com.hospitaliq.patientservice.dto.PaginatedResponse;
import com.hospitaliq.patientservice.dto.PatientDetailResponse;
import com.hospitaliq.patientservice.dto.PatientListResponse;
import com.hospitaliq.patientservice.dto.PatientStatsResponse;
import com.hospitaliq.patientservice.dto.VirusListResponse;
import com.hospitaliq.patientservice.service.PatientService;
import com.hospitaliq.patientservice.util.PaginationUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

/**
 * REST controller for managing patient data.
 *
 * <p>Why this is structured this way:
 * Controllers in Spring Boot should act strictly as HTTP routers. Their only job is to:
 * 1. Receive the HTTP Request
 * 2. Validate input parameters (e.g., using @Min, @Max)
 * 3. Delegate business logic to the Service layer
 * 4. Return the HTTP Response
 * 
 * You will notice there is ZERO business logic or data mapping in this class.
 * This makes the code highly testable and easy to read.
 */
@RestController
@RequestMapping("/api/v1/patients")
@Validated // Enables Spring's method-level validation for query parameters
public class PatientController {

    private final PatientService patientService;

    // Constructor injection is preferred over @Autowired field injection for better testability
    public PatientController(PatientService patientService) {
        this.patientService = patientService;
    }

    // -------------------------------------------------------------------------
    // PUBLIC ENDPOINTS
    // -------------------------------------------------------------------------

    /**
     * Retrieves a paginated list of patients, optionally filtered by search term or state.
     */
    @GetMapping
    public ResponseEntity<PaginatedResponse<PatientListResponse>> listPatients(
            @RequestParam(defaultValue = AppConstants.DEFAULT_PAGE_SKIP) @Min(0) int skip,
            @RequestParam(defaultValue = AppConstants.DEFAULT_PAGE_LIMIT) @Min(1) @Max(100) int limit,
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String state,
            @RequestParam(required = false) String offset) {

        // We extract the adapter logic (handling 'offset' vs 'skip') into a utility class
        // so the controller remains purely focused on routing.
        int resolvedSkip = PaginationUtil.resolveSkip(skip, offset);

        PaginatedResponse<PatientListResponse> response = patientService.listPatients(search, state, resolvedSkip, limit);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the comprehensive medical history for a specific patient.
     */
    @GetMapping("/{patientId}")
    public ResponseEntity<PatientDetailResponse> getPatient(@PathVariable Integer patientId) {
        PatientDetailResponse response = patientService.getPatientDetail(patientId);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves a list of all viruses currently registered in the system.
     * Note: This is a public endpoint (no JWT required) as configured in SecurityConfig.
     */
    @GetMapping("/viruses/list")
    public ResponseEntity<VirusListResponse> listViruses() {
        VirusListResponse response = patientService.listViruses();
        return ResponseEntity.ok(response);
    }

    /**
     * Aggregate patient population statistics (total count, avg age, etc.).
     * Note: This is a public endpoint (no JWT required).
     */
    @GetMapping("/stats")
    public ResponseEntity<PatientStatsResponse> getPatientStats() {
        PatientStatsResponse response = patientService.getPatientStats();
        return ResponseEntity.ok(response);
    }
}
