package com.hospitaliq.patientservice.repository;

import com.hospitaliq.patientservice.entity.TravelHistoryEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TravelHistoryRepository extends JpaRepository<TravelHistoryEntity, Integer> {
    List<TravelHistoryEntity> findByPatientIdOrderByTravelDateDesc(Integer patientId);
}
