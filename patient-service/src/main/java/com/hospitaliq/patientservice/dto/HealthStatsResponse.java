package com.hospitaliq.patientservice.dto;

import java.time.Instant;
import java.util.Map;

/**
 * Response DTO for {@code GET /api/v1/health-stats}.
 *
 * <p>Contains aggregate patient population statistics, a cache-freshness
 * timestamp, and the total patient count. Designed for dashboard consumption.
 *
 * <p>Uses Java 16+ records for immutability and auto-generated equals/hashCode/toString.
 * Jackson serialises records correctly with SNAKE_CASE naming strategy.
 *
 * @param totalPatients       total number of patients in the system
 * @param atRiskCount         patients with age &gt; 60 OR pre-existing conditions
 * @param avgAge              average patient age, rounded to 1 decimal place
 * @param bloodGroupDistribution  blood group → count mapping
 * @param cachedAt            ISO-8601 UTC timestamp when this snapshot was computed
 */
public record HealthStatsResponse(
        long totalPatients,
        long atRiskCount,
        double avgAge,
        Map<String, Long> bloodGroupDistribution,
        String cachedAt
) {
    /** Convenience constructor that fills {@code cachedAt} with the current UTC time. */
    public HealthStatsResponse(long totalPatients, long atRiskCount,
                               double avgAge, Map<String, Long> bloodGroupDistribution) {
        this(totalPatients, atRiskCount, avgAge, bloodGroupDistribution,
             Instant.now().toString());
    }
}
