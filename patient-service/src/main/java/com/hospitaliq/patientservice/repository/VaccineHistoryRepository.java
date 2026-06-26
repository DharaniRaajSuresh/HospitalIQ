package com.hospitaliq.patientservice.repository;

import com.hospitaliq.patientservice.entity.VaccineHistoryEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface VaccineHistoryRepository extends JpaRepository<VaccineHistoryEntity, Integer> {
    List<VaccineHistoryEntity> findByPatientIdOrderByVaccinationDateDesc(Integer patientId);
}
