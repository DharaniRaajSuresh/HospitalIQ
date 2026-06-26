package com.hospitaliq.patientservice.service;

import com.hospitaliq.patientservice.dto.PaginatedResponse;
import com.hospitaliq.patientservice.dto.PatientDetailResponse;
import com.hospitaliq.patientservice.dto.PatientListResponse;
import com.hospitaliq.patientservice.dto.PatientStatsResponse;
import com.hospitaliq.patientservice.dto.VirusListResponse;
import com.hospitaliq.patientservice.entity.*;
import com.hospitaliq.patientservice.exception.PatientNotFoundException;
import com.hospitaliq.patientservice.mapper.PatientMapper;
import com.hospitaliq.patientservice.repository.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Core business logic service for Patient operations.
 * 
 * <p>Architectural highlights:
 * <ul>
 *   <li><b>Read-Only Transactions:</b> All methods run in a read-only transaction by default for performance.</li>
 *   <li><b>Separation of Concerns:</b> Uses {@link PatientMapper} to map Entities to DTOs, keeping this service strictly focused on data retrieval and business logic.</li>
 *   <li><b>Dependency Injection:</b> All repositories and mappers are constructor-injected for testability.</li>
 * </ul>
 */
@Service
@Transactional(readOnly = true)
public class PatientService {

    private final PatientRepository patientRepo;
    private final VaccineHistoryRepository vaccineRepo;
    private final TravelHistoryRepository travelRepo;
    private final FamilyHistoryRepository familyRepo;
    private final VirusRegistryRepository virusRepo;
    private final PatientMapper patientMapper;

    public PatientService(PatientRepository patientRepo,
                          VaccineHistoryRepository vaccineRepo,
                          TravelHistoryRepository travelRepo,
                          FamilyHistoryRepository familyRepo,
                          VirusRegistryRepository virusRepo,
                          PatientMapper patientMapper) {
        this.patientRepo = patientRepo;
        this.vaccineRepo = vaccineRepo;
        this.travelRepo = travelRepo;
        this.familyRepo = familyRepo;
        this.virusRepo = virusRepo;
        this.patientMapper = patientMapper;
    }

    // -------------------------------------------------------------------------
    // PUBLIC METHODS
    // -------------------------------------------------------------------------

    /**
     * Lists patients with pagination, supporting optional search and state filters.
     * 
     * @return A paginated wrapper containing PatientListResponse DTOs.
     */
    public PaginatedResponse<PatientListResponse> listPatients(String search, String state, int skip, int limit) {
        int page = skip / limit;
        Sort sort = Sort.by(Sort.Direction.DESC, "id");
        PageRequest pageRequest = PageRequest.of(page, limit, sort);

        Page<PatientEntity> pageResult;
        long total;

        if (hasSearchFilters(search, state)) {
            String searchParam = search != null ? search.trim() : null;
            String stateParam = state != null ? state.trim() : null;
            pageResult = patientRepo.searchPatients(searchParam, stateParam, pageRequest);
            total = patientRepo.countSearchPatients(searchParam, stateParam);
        } else {
            pageResult = patientRepo.findAll(pageRequest);
            total = patientRepo.count();
        }

        // Delegate mapping to PatientMapper to keep the service clean
        List<PatientListResponse> patients = pageResult.getContent()
                .stream()
                .map(patientMapper::toListResponse)
                .collect(Collectors.toList());

        return new PaginatedResponse<>(patients, total, skip, limit);
    }

    /**
     * Aggregates a patient's core profile along with their full medical history.
     * 
     * @throws PatientNotFoundException if the ID does not exist.
     */
    public PatientDetailResponse getPatientDetail(Integer patientId) {
        PatientEntity patient = patientRepo.findById(patientId)
                .orElseThrow(() -> new PatientNotFoundException(patientId));

        // Fetch related histories. In a production scenario with millions of rows, 
        // this might be optimized using JPA @EntityGraph or customized queries to avoid the N+1 problem.
        List<VaccineHistoryEntity> vaccines = vaccineRepo.findByPatientIdOrderByVaccinationDateDesc(patientId);
        List<TravelHistoryEntity> travels = travelRepo.findByPatientIdOrderByTravelDateDesc(patientId);
        List<FamilyHistoryEntity> families = familyRepo.findByPatientId(patientId);

        return patientMapper.toDetailResponse(patient, vaccines, travels, families);
    }

    /**
     * Retrieves all registered viruses for dropdowns and general info.
     */
    public VirusListResponse listViruses() {
        List<VirusRegistryEntity> viruses = virusRepo.findAllByOrderByVirusNameAsc();
        return new VirusListResponse(viruses);
    }

    /**
     * Returns aggregate statistics across the entire patient population.
     * 
     * <p>Why we do it this way: 
     * We use JPA JPQL aggregate queries (e.g., AVG, COUNT) directly on the database. 
     * This is significantly more efficient than pulling all rows into memory and calculating in Java.
     */
    public PatientStatsResponse getPatientStats() {
        long total = patientRepo.count();
        
        Double avgAgeRaw = patientRepo.getAverageAge();
        double avgAge = avgAgeRaw != null ? Math.round(avgAgeRaw * 10.0) / 10.0 : 0.0;
        
        long atRiskCount = patientRepo.countAtRisk();

        List<Object[]> bloodGroupRows = patientRepo.getBloodGroupDistribution();
        Map<String, Long> bloodGroupDistribution = parseBloodGroupDistribution(bloodGroupRows);

        return new PatientStatsResponse(total, avgAge, atRiskCount, bloodGroupDistribution);
    }

    // -------------------------------------------------------------------------
    // PRIVATE HELPER METHODS
    // -------------------------------------------------------------------------

    private boolean hasSearchFilters(String search, String state) {
        return (search != null && !search.isBlank()) || (state != null && !state.isBlank());
    }

    private Map<String, Long> parseBloodGroupDistribution(List<Object[]> bloodGroupRows) {
        Map<String, Long> distribution = new LinkedHashMap<>();
        for (Object[] row : bloodGroupRows) {
            String group = row[0] != null ? row[0].toString() : "Unknown";
            long count = ((Number) row[1]).longValue();
            distribution.put(group, count);
        }
        return distribution;
    }
}
