package com.hospitaliq.patientservice;

import com.hospitaliq.patientservice.entity.PatientEntity;
import com.hospitaliq.patientservice.repository.PatientRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.TestPropertySource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Repository layer tests using @DataJpaTest with an in-memory H2 database.
 * Validates JPQL queries: searchPatients, countAtRisk, getAverageAge, getBloodGroupDistribution.
 */
@DataJpaTest
@TestPropertySource(properties = {
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.H2Dialect"
})
class PatientRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private PatientRepository patientRepository;

    @BeforeEach
    void setUp() {
        PatientEntity p1 = new PatientEntity();
        p1.setPatientName("Ravi Kumar");
        p1.setAge(72);
        p1.setBloodGroup("A+");
        p1.setGender("Male");
        p1.setState("Karnataka");
        p1.setPreExistingConditions("Diabetes, Hypertension");
        entityManager.persist(p1);

        PatientEntity p2 = new PatientEntity();
        p2.setPatientName("Sunita Sharma");
        p2.setAge(35);
        p2.setBloodGroup("B+");
        p2.setGender("Female");
        p2.setState("Maharashtra");
        p2.setPreExistingConditions(null);
        entityManager.persist(p2);

        PatientEntity p3 = new PatientEntity();
        p3.setPatientName("Amit Patel");
        p3.setAge(58);
        p3.setBloodGroup("A+");
        p3.setGender("Male");
        p3.setState("Gujarat");
        p3.setPreExistingConditions("");
        entityManager.persist(p3);

        entityManager.flush();
    }

    @Test
    @DisplayName("searchPatients: name match returns correct patient")
    void searchByName_returnsMatchingPatient() {
        Page<PatientEntity> result = patientRepository.searchPatients(
                "ravi", null, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).getPatientName()).isEqualTo("Ravi Kumar");
    }

    @Test
    @DisplayName("searchPatients: state filter returns only that state's patients")
    void searchByState_returnsOnlyMatchingState() {
        Page<PatientEntity> result = patientRepository.searchPatients(
                null, "Karnataka", PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).getState()).isEqualTo("Karnataka");
    }

    @Test
    @DisplayName("searchPatients: null params returns all patients")
    void searchWithNullParams_returnsAll() {
        Page<PatientEntity> result = patientRepository.searchPatients(
                null, null, PageRequest.of(0, 10));

        assertThat(result.getTotalElements()).isEqualTo(3);
    }

    @Test
    @DisplayName("getAverageAge: returns correct average of persisted patients")
    void getAverageAge_returnsCorrectValue() {
        Double avg = patientRepository.getAverageAge();
        // (72 + 35 + 58) / 3 = 55.0
        assertThat(avg).isEqualTo(55.0);
    }

    @Test
    @DisplayName("countAtRisk: counts patients with age > 60 OR pre-existing conditions")
    void countAtRisk_countsCorrectly() {
        // p1: age 72 AND has conditions → at risk
        // p2: age 35, no conditions → not at risk
        // p3: age 58, empty conditions string → not at risk
        long count = patientRepository.countAtRisk();
        assertThat(count).isEqualTo(1);
    }

    @Test
    @DisplayName("getBloodGroupDistribution: groups patients by blood group correctly")
    void getBloodGroupDistribution_groupsCorrectly() {
        List<Object[]> rows = patientRepository.getBloodGroupDistribution();
        assertThat(rows).isNotEmpty();

        long aPlus = rows.stream()
                .filter(r -> "A+".equals(r[0]))
                .mapToLong(r -> ((Number) r[1]).longValue())
                .sum();
        assertThat(aPlus).isEqualTo(2); // p1 and p3 both A+
    }
}
