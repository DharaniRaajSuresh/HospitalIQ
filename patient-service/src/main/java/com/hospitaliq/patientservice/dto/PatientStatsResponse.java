package com.hospitaliq.patientservice.dto;

import java.util.Map;

/**
 * Response DTO for the GET /api/v1/patients/stats endpoint.
 * Aggregated from the patients table via JPA queries.
 */
public class PatientStatsResponse {

    private long totalPatients;
    private double avgAge;
    private long atRiskCount;
    private Map<String, Long> bloodGroupDistribution;

    public PatientStatsResponse(long totalPatients,
                                 double avgAge,
                                 long atRiskCount,
                                 Map<String, Long> bloodGroupDistribution) {
        this.totalPatients = totalPatients;
        this.avgAge = avgAge;
        this.atRiskCount = atRiskCount;
        this.bloodGroupDistribution = bloodGroupDistribution;
    }

    public long getTotalPatients() { return totalPatients; }
    public double getAvgAge() { return avgAge; }
    public long getAtRiskCount() { return atRiskCount; }
    public Map<String, Long> getBloodGroupDistribution() { return bloodGroupDistribution; }
}
