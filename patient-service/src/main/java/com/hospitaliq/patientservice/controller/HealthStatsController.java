package com.hospitaliq.patientservice.controller;

import com.hospitaliq.patientservice.dto.HealthStatsResponse;
import com.hospitaliq.patientservice.service.HealthStatsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller exposing aggregate health statistics for the patient population.
 *
 * <p>Endpoint: {@code GET /api/v1/health-stats}
 *
 * <p>Architecture notes:
 * <ul>
 *   <li>Returns data from a 5-minute in-memory cache (see {@link HealthStatsService})
 *       to avoid repeated DB aggregation queries on each dashboard poll.</li>
 *   <li>Publicly accessible (no JWT required) — configured in
 *       {@link com.hospitaliq.patientservice.config.SecurityConfig} — so the frontend
 *       can display patient counts on the landing page before login.</li>
 *   <li>Response uses a Java record ({@link HealthStatsResponse}) with a {@code cached_at}
 *       field so the consumer knows data freshness.</li>
 * </ul>
 *
 * <p>This controller demonstrates the second Spring Boot {@code @RestController} in the
 * patient-service, alongside {@link PatientController}, illustrating how different concerns
 * are separated into dedicated controllers in a production microservice.
 */
@RestController
@RequestMapping("/api/v1/health-stats")
public class HealthStatsController {

    private final HealthStatsService healthStatsService;

    public HealthStatsController(HealthStatsService healthStatsService) {
        this.healthStatsService = healthStatsService;
    }

    /**
     * Returns aggregate patient statistics: total count, at-risk count, average age,
     * blood group distribution, and the timestamp when the cache was last refreshed.
     *
     * <p>The response is served from an in-memory cache refreshed every 5 minutes
     * via {@code @Scheduled}. The {@code cached_at} field indicates data freshness.
     *
     * @return {@link HealthStatsResponse} with aggregate population statistics
     */
    @GetMapping
    public ResponseEntity<HealthStatsResponse> getHealthStats() {
        return ResponseEntity.ok(healthStatsService.getStats());
    }
}
