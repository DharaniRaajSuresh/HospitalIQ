package com.hospitaliq.patientservice.service;

import com.hospitaliq.patientservice.dto.HealthStatsResponse;
import com.hospitaliq.patientservice.repository.PatientRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Service for aggregate health statistics across the patient population.
 *
 * <p>Uses a {@link AtomicReference} in-memory cache refreshed every 5 minutes
 * via {@link Scheduled}. This avoids 4 DB round-trips on every dashboard call
 * while keeping the stats reasonably fresh.
 *
 * <p>Cache strategy rationale:
 * <ul>
 *   <li>Patient stats change infrequently (admits, discharges) — 5min staleness acceptable</li>
 *   <li>{@code AtomicReference} is lock-free and thread-safe for single-writer, many-reader pattern</li>
 *   <li>First request before the scheduler fires triggers an eager load via {@link #getStats()}</li>
 * </ul>
 */
@Service
@Transactional(readOnly = true)
public class HealthStatsService {

    private static final Logger log = LoggerFactory.getLogger(HealthStatsService.class);

    private final PatientRepository patientRepo;

    /** Lock-free cache — written only by the scheduler, read by many web threads. */
    private final AtomicReference<HealthStatsResponse> cache = new AtomicReference<>();

    public HealthStatsService(PatientRepository patientRepo) {
        this.patientRepo = patientRepo;
    }

    /**
     * Returns cached stats, computing them eagerly if the cache is cold (first request).
     */
    public HealthStatsResponse getStats() {
        HealthStatsResponse cached = cache.get();
        if (cached == null) {
            log.info("Health stats cache cold — computing eagerly");
            cached = computeStats();
            cache.set(cached);
        }
        return cached;
    }

    /**
     * Refreshes the stats cache every 5 minutes.
     * {@code @EnableScheduling} on {@link com.hospitaliq.patientservice.PatientServiceApplication}
     * activates this method.
     */
    @Scheduled(fixedRate = 300_000)   // every 5 minutes
    public void refreshCache() {
        log.info("Refreshing health stats cache (scheduled)");
        try {
            HealthStatsResponse fresh = computeStats();
            cache.set(fresh);
            log.info("Health stats cache refreshed — totalPatients={}, atRisk={}",
                    fresh.totalPatients(), fresh.atRiskCount());
        } catch (Exception e) {
            log.error("Health stats cache refresh failed — keeping stale data", e);
        }
    }

    // ---------------------------------------------------------------------------
    // Private helpers
    // ---------------------------------------------------------------------------

    private HealthStatsResponse computeStats() {
        long total = patientRepo.count();

        Double avgAgeRaw = patientRepo.getAverageAge();
        double avgAge = avgAgeRaw != null ? Math.round(avgAgeRaw * 10.0) / 10.0 : 0.0;

        long atRisk = patientRepo.countAtRisk();

        List<Object[]> bloodGroupRows = patientRepo.getBloodGroupDistribution();
        Map<String, Long> bloodGroupDistribution = new LinkedHashMap<>();
        for (Object[] row : bloodGroupRows) {
            String group = row[0] != null ? row[0].toString() : "Unknown";
            long count = ((Number) row[1]).longValue();
            bloodGroupDistribution.put(group, count);
        }

        return new HealthStatsResponse(total, atRisk, avgAge, bloodGroupDistribution);
    }
}
