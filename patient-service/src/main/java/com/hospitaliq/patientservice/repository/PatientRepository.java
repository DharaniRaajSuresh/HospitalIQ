package com.hospitaliq.patientservice.repository;

import com.hospitaliq.patientservice.entity.PatientEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PatientRepository extends JpaRepository<PatientEntity, Integer> {

    Page<PatientEntity> findByState(String state, Pageable pageable);

    @Query("SELECT p FROM PatientEntity p WHERE " +
           "(:search IS NULL OR LOWER(p.patientName) LIKE LOWER(CONCAT('%', :search, '%'))) AND " +
           "(:state IS NULL OR p.state = :state)")
    Page<PatientEntity> searchPatients(@Param("search") String search,
                                       @Param("state") String state,
                                       Pageable pageable);

    @Query("SELECT COUNT(p) FROM PatientEntity p WHERE " +
           "(:search IS NULL OR LOWER(p.patientName) LIKE LOWER(CONCAT('%', :search, '%'))) AND " +
           "(:state IS NULL OR p.state = :state)")
    long countSearchPatients(@Param("search") String search, @Param("state") String state);

    @Query("SELECT AVG(p.age) FROM PatientEntity p")
    Double getAverageAge();

    /**
     * Returns blood group distribution as pairs of [bloodGroup, count].
     * Used by the /patients/stats endpoint.
     */
    @Query("SELECT p.bloodGroup, COUNT(p) FROM PatientEntity p GROUP BY p.bloodGroup")
    List<Object[]> getBloodGroupDistribution();

    /**
     * Counts patients considered at-risk: age over 60 OR has pre-existing conditions recorded.
     */
    @Query("SELECT COUNT(p) FROM PatientEntity p WHERE p.age > 60 OR " +
           "(p.preExistingConditions IS NOT NULL AND p.preExistingConditions <> '')")
    long countAtRisk();
}

