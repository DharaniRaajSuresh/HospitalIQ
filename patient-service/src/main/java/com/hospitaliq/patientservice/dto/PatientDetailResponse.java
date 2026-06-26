package com.hospitaliq.patientservice.dto;

import java.util.List;

/**
 * DTO for representing comprehensive patient details including medical histories.
 * Kept strictly as a data carrier without internal mapping logic.
 */
public class PatientDetailResponse {

    private PatientDetail patient;
    private List<VaccineRecord> vaccineHistory;
    private List<TravelRecord> travelHistory;
    private List<FamilyRecord> familyHistory;

    public PatientDetailResponse() {}

    public PatientDetailResponse(PatientDetail patient,
                                  List<VaccineRecord> vaccineHistory,
                                  List<TravelRecord> travelHistory,
                                  List<FamilyRecord> familyHistory) {
        this.patient = patient;
        this.vaccineHistory = vaccineHistory;
        this.travelHistory = travelHistory;
        this.familyHistory = familyHistory;
    }

    public PatientDetail getPatient() { return patient; }
    public void setPatient(PatientDetail patient) { this.patient = patient; }

    public List<VaccineRecord> getVaccineHistory() { return vaccineHistory; }
    public void setVaccineHistory(List<VaccineRecord> vaccineHistory) { this.vaccineHistory = vaccineHistory; }

    public List<TravelRecord> getTravelHistory() { return travelHistory; }
    public void setTravelHistory(List<TravelRecord> travelHistory) { this.travelHistory = travelHistory; }

    public List<FamilyRecord> getFamilyHistory() { return familyHistory; }
    public void setFamilyHistory(List<FamilyRecord> familyHistory) { this.familyHistory = familyHistory; }

    public static class PatientDetail {
        private Integer id;
        private String patientName;
        private String dob;
        private Integer age;
        private String bloodGroup;
        private String gender;
        private String contact;
        private String address;
        private String state;
        private String district;
        private String preExistingConditions;

        public PatientDetail() {}

        public Integer getId() { return id; }
        public void setId(Integer id) { this.id = id; }

        public String getPatientName() { return patientName; }
        public void setPatientName(String patientName) { this.patientName = patientName; }

        public String getDob() { return dob; }
        public void setDob(String dob) { this.dob = dob; }

        public Integer getAge() { return age; }
        public void setAge(Integer age) { this.age = age; }

        public String getBloodGroup() { return bloodGroup; }
        public void setBloodGroup(String bloodGroup) { this.bloodGroup = bloodGroup; }

        public String getGender() { return gender; }
        public void setGender(String gender) { this.gender = gender; }

        public String getContact() { return contact; }
        public void setContact(String contact) { this.contact = contact; }

        public String getAddress() { return address; }
        public void setAddress(String address) { this.address = address; }

        public String getState() { return state; }
        public void setState(String state) { this.state = state; }

        public String getDistrict() { return district; }
        public void setDistrict(String district) { this.district = district; }

        public String getPreExistingConditions() { return preExistingConditions; }
        public void setPreExistingConditions(String preExistingConditions) { this.preExistingConditions = preExistingConditions; }
    }

    public static class VaccineRecord {
        private Integer id;
        private String vaccineName;
        private Integer doseNumber;
        private String vaccinationDate;
        private String hospitalName;
        private String virusName;
        private Double effectiveness;

        public VaccineRecord() {}

        public Integer getId() { return id; }
        public void setId(Integer id) { this.id = id; }

        public String getVaccineName() { return vaccineName; }
        public void setVaccineName(String vaccineName) { this.vaccineName = vaccineName; }

        public Integer getDoseNumber() { return doseNumber; }
        public void setDoseNumber(Integer doseNumber) { this.doseNumber = doseNumber; }

        public String getVaccinationDate() { return vaccinationDate; }
        public void setVaccinationDate(String vaccinationDate) { this.vaccinationDate = vaccinationDate; }

        public String getHospitalName() { return hospitalName; }
        public void setHospitalName(String hospitalName) { this.hospitalName = hospitalName; }

        public String getVirusName() { return virusName; }
        public void setVirusName(String virusName) { this.virusName = virusName; }

        public Double getEffectiveness() { return effectiveness; }
        public void setEffectiveness(Double effectiveness) { this.effectiveness = effectiveness; }
    }

    public static class TravelRecord {
        private Integer id;
        private String fromLocation;
        private String toLocation;
        private String travelDate;
        private String returnDate;
        private String purpose;

        public TravelRecord() {}

        public Integer getId() { return id; }
        public void setId(Integer id) { this.id = id; }

        public String getFromLocation() { return fromLocation; }
        public void setFromLocation(String fromLocation) { this.fromLocation = fromLocation; }

        public String getToLocation() { return toLocation; }
        public void setToLocation(String toLocation) { this.toLocation = toLocation; }

        public String getTravelDate() { return travelDate; }
        public void setTravelDate(String travelDate) { this.travelDate = travelDate; }

        public String getReturnDate() { return returnDate; }
        public void setReturnDate(String returnDate) { this.returnDate = returnDate; }

        public String getPurpose() { return purpose; }
        public void setPurpose(String purpose) { this.purpose = purpose; }
    }

    public static class FamilyRecord {
        private Integer id;
        private String relationship;
        private String condition;
        private Integer ageAtDiagnosis;
        private Boolean isDeceased;

        public FamilyRecord() {}

        public Integer getId() { return id; }
        public void setId(Integer id) { this.id = id; }

        public String getRelationship() { return relationship; }
        public void setRelationship(String relationship) { this.relationship = relationship; }

        public String getCondition() { return condition; }
        public void setCondition(String condition) { this.condition = condition; }

        public Integer getAgeAtDiagnosis() { return ageAtDiagnosis; }
        public void setAgeAtDiagnosis(Integer ageAtDiagnosis) { this.ageAtDiagnosis = ageAtDiagnosis; }

        public Boolean getIsDeceased() { return isDeceased; }
        public void setIsDeceased(Boolean isDeceased) { this.isDeceased = isDeceased; }
    }
}
