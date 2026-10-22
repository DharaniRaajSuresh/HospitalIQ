package com.hospitaliq.patientservice.mapper;

import com.hospitaliq.patientservice.dto.PatientDetailResponse;
import com.hospitaliq.patientservice.dto.PatientListResponse;
import com.hospitaliq.patientservice.entity.*;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Mapper class responsible for converting Entities to Data Transfer Objects (DTOs).
 * 
 * <p>Why this exists: 
 * We want to keep our DTOs strictly as data carriers with no knowledge of the persistence layer (Entities).
 * Similarly, the Service layer orchestrates logic, but shouldn't be cluttered with manual field-by-field mapping.
 * Extracting this to a Mapper component follows the Single Responsibility Principle and keeps code clean.
 */
@Component
public class PatientMapper {

    /**
     * Converts a PatientEntity into a PatientListResponse (used for list views).
     */
    public PatientListResponse toListResponse(PatientEntity entity) {
        if (entity == null) return null;
        
        PatientListResponse response = new PatientListResponse();
        response.setId(entity.getId());
        response.setPatientName(entity.getPatientName());
        response.setAge(entity.getAge());
        response.setBloodGroup(entity.getBloodGroup());
        response.setGender(entity.getGender());
        response.setState(entity.getState());
        response.setDistrict(entity.getDistrict());
        response.setPreExistingConditions(entity.getPreExistingConditions());
        
        return response;
    }

    /**
     * Converts a PatientEntity and their related histories into a comprehensive PatientDetailResponse.
     */
    public PatientDetailResponse toDetailResponse(PatientEntity patient,
                                                  List<VaccineHistoryEntity> vaccines,
                                                  List<TravelHistoryEntity> travels,
                                                  List<FamilyHistoryEntity> families) {
        
        PatientDetailResponse.PatientDetail detail = new PatientDetailResponse.PatientDetail();
        detail.setId(patient.getId());
        detail.setPatientName(patient.getPatientName());
        detail.setDob(patient.getDob() != null ? patient.getDob().toString() : null);
        detail.setAge(patient.getAge());
        detail.setBloodGroup(patient.getBloodGroup());
        detail.setGender(patient.getGender());
        detail.setContact(patient.getContact());
        detail.setAddress(patient.getAddress());
        detail.setState(patient.getState());
        detail.setDistrict(patient.getDistrict());
        detail.setPreExistingConditions(patient.getPreExistingConditions());

        List<PatientDetailResponse.VaccineRecord> vaccineRecords = vaccines.stream().map(v -> {
            PatientDetailResponse.VaccineRecord r = new PatientDetailResponse.VaccineRecord();
            r.setId(v.getId());
            r.setVaccineName(v.getVaccineName());
            r.setDoseNumber(v.getDoseNumber());
            r.setVaccinationDate(v.getVaccinationDate() != null ? v.getVaccinationDate().toString() : null);
            r.setHospitalName(v.getHospitalName());
            r.setVirusName(v.getVirusName());
            r.setEffectiveness(v.getEffectiveness());
            return r;
        }).collect(Collectors.toList());

        List<PatientDetailResponse.TravelRecord> travelRecords = travels.stream().map(t -> {
            PatientDetailResponse.TravelRecord r = new PatientDetailResponse.TravelRecord();
            r.setId(t.getId());
            r.setFromLocation(t.getFromLocation());
            r.setToLocation(t.getToLocation());
            r.setTravelDate(t.getTravelDate() != null ? t.getTravelDate().toString() : null);
            r.setReturnDate(t.getReturnDate() != null ? t.getReturnDate().toString() : null);
            r.setPurpose(t.getPurpose());
            return r;
        }).collect(Collectors.toList());

        List<PatientDetailResponse.FamilyRecord> familyRecords = families.stream().map(f -> {
            PatientDetailResponse.FamilyRecord r = new PatientDetailResponse.FamilyRecord();
            r.setId(f.getId());
            r.setRelationship(f.getRelationship());
            r.setCondition(f.getCondition());
            r.setAgeAtDiagnosis(f.getAgeAtDiagnosis());
            r.setIsDeceased(f.getIsDeceased());
            return r;
        }).collect(Collectors.toList());

        return new PatientDetailResponse(detail, vaccineRecords, travelRecords, familyRecords);
    }
}
