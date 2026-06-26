package com.hospitaliq.patientservice.repository;

import com.hospitaliq.patientservice.entity.VirusRegistryEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface VirusRegistryRepository extends JpaRepository<VirusRegistryEntity, Integer> {
    List<VirusRegistryEntity> findAllByOrderByVirusNameAsc();
}
