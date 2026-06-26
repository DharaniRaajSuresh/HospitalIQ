package com.hospitaliq.patientservice;

import com.hospitaliq.patientservice.dto.PaginatedResponse;
import com.hospitaliq.patientservice.dto.PatientDetailResponse;
import com.hospitaliq.patientservice.dto.PatientStatsResponse;
import com.hospitaliq.patientservice.entity.*;
import com.hospitaliq.patientservice.exception.PatientNotFoundException;
import com.hospitaliq.patientservice.repository.*;
import com.hospitaliq.patientservice.service.PatientService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Pure unit tests for PatientService using Mockito.
 * No Spring context loaded — repositories are mocked.
 */
@ExtendWith(MockitoExtension.class)
class PatientServiceTest {

    @Mock private PatientRepository patientRepo;
    @Mock private VaccineHistoryRepository vaccineRepo;
    @Mock private TravelHistoryRepository travelRepo;
    @Mock private FamilyHistoryRepository familyRepo;
    @Mock private VirusRegistryRepository virusRepo;
    
    private com.hospitaliq.patientservice.mapper.PatientMapper patientMapper = new com.hospitaliq.patientservice.mapper.PatientMapper();

    private PatientService patientService;

    private PatientEntity samplePatient;

    @BeforeEach
    void setUp() {
        patientService = new PatientService(patientRepo, vaccineRepo, travelRepo, familyRepo, virusRepo, patientMapper);
        
        samplePatient = new PatientEntity();
        samplePatient.setId(1);
        samplePatient.setPatientName("Ravi Kumar");
        samplePatient.setAge(45);
        samplePatient.setBloodGroup("A+");
        samplePatient.setGender("Male");
        samplePatient.setState("Karnataka");
    }

    // ------------------------------------------------------------------
    // listPatients
    // ------------------------------------------------------------------

    @Test
    @DisplayName("listPatients: no filters uses findAll and count()")
    void listPatients_noFilters_usesFindAll() {
        when(patientRepo.findAll(any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(samplePatient)));
        when(patientRepo.count()).thenReturn(1L);

        PaginatedResponse<?> result = patientService.listPatients(null, null, 0, 20);

        assertThat(result.getTotal()).isEqualTo(1L);
        assertThat(result.getPatients()).hasSize(1);
        verify(patientRepo).findAll(any(PageRequest.class));
        verify(patientRepo).count();
    }

    @Test
    @DisplayName("listPatients: with search uses searchPatients query")
    void listPatients_withSearch_usesSearchQuery() {
        when(patientRepo.searchPatients(eq("ravi"), isNull(), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(samplePatient)));
        when(patientRepo.countSearchPatients(eq("ravi"), isNull())).thenReturn(1L);

        PaginatedResponse<?> result = patientService.listPatients("ravi", null, 0, 20);

        assertThat(result.getTotal()).isEqualTo(1L);
        verify(patientRepo).searchPatients(eq("ravi"), isNull(), any(PageRequest.class));
    }

    @Test
    @DisplayName("listPatients: skip=20, limit=20 maps to page=1")
    void listPatients_correctPageCalculation() {
        when(patientRepo.findAll(any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(patientRepo.count()).thenReturn(50L);

        PaginatedResponse<?> result = patientService.listPatients(null, null, 20, 20);

        assertThat(result.getSkip()).isEqualTo(20);
        assertThat(result.getLimit()).isEqualTo(20);
    }

    // ------------------------------------------------------------------
    // getPatientDetail
    // ------------------------------------------------------------------

    @Test
    @DisplayName("getPatientDetail: fetches patient + all 3 history tables")
    void getPatientDetail_fetchesAllHistories() {
        when(patientRepo.findById(1)).thenReturn(Optional.of(samplePatient));
        when(vaccineRepo.findByPatientIdOrderByVaccinationDateDesc(1)).thenReturn(List.of());
        when(travelRepo.findByPatientIdOrderByTravelDateDesc(1)).thenReturn(List.of());
        when(familyRepo.findByPatientId(1)).thenReturn(List.of());

        PatientDetailResponse response = patientService.getPatientDetail(1);

        assertThat(response).isNotNull();
        verify(vaccineRepo).findByPatientIdOrderByVaccinationDateDesc(1);
        verify(travelRepo).findByPatientIdOrderByTravelDateDesc(1);
        verify(familyRepo).findByPatientId(1);
    }

    @Test
    @DisplayName("getPatientDetail: throws PatientNotFoundException for unknown ID")
    void getPatientDetail_notFound_throwsException() {
        when(patientRepo.findById(999)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> patientService.getPatientDetail(999))
                .isInstanceOf(PatientNotFoundException.class);
    }

    // ------------------------------------------------------------------
    // getPatientStats
    // ------------------------------------------------------------------

    @Test
    @DisplayName("getPatientStats: assembles all aggregate query results correctly")
    void getPatientStats_returnsCorrectValues() {
        when(patientRepo.count()).thenReturn(10000L);
        when(patientRepo.getAverageAge()).thenReturn(52.347);
        when(patientRepo.countAtRisk()).thenReturn(2340L);
        when(patientRepo.getBloodGroupDistribution()).thenReturn(List.of(
                new Object[]{"A+", 3200L},
                new Object[]{"B+", 2800L}
        ));

        PatientStatsResponse stats = patientService.getPatientStats();

        assertThat(stats.getTotalPatients()).isEqualTo(10000L);
        assertThat(stats.getAvgAge()).isEqualTo(52.3); // rounded to 1 dp
        assertThat(stats.getAtRiskCount()).isEqualTo(2340L);
        assertThat(stats.getBloodGroupDistribution()).containsEntry("A+", 3200L);
    }

    @Test
    @DisplayName("getPatientStats: handles null avgAge gracefully")
    void getPatientStats_nullAvgAge_returnsZero() {
        when(patientRepo.count()).thenReturn(0L);
        when(patientRepo.getAverageAge()).thenReturn(null);
        when(patientRepo.countAtRisk()).thenReturn(0L);
        when(patientRepo.getBloodGroupDistribution()).thenReturn(List.of());

        PatientStatsResponse stats = patientService.getPatientStats();

        assertThat(stats.getAvgAge()).isEqualTo(0.0);
    }
}
