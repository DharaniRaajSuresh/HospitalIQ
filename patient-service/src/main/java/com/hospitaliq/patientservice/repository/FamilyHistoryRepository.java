package com.hospitaliq.patientservice.repository;

import com.hospitaliq.patientservice.entity.FamilyHistoryEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface FamilyHistoryRepository extends JpaRepository<FamilyHistoryEntity, Integer> {
    List<FamilyHistoryEntity> findByPatientId(Integer patientId);
}
