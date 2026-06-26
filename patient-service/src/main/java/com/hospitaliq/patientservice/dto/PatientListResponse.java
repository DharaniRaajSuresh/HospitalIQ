package com.hospitaliq.patientservice.dto;


public class PatientListResponse {

    private Integer id;
    private String patientName;
    private Integer age;
    private String bloodGroup;
    private String gender;
    private String state;
    private String district;
    private String preExistingConditions;

    public PatientListResponse() {}

    public void setId(Integer id) { this.id = id; }
    public void setPatientName(String patientName) { this.patientName = patientName; }
    public void setAge(Integer age) { this.age = age; }
    public void setBloodGroup(String bloodGroup) { this.bloodGroup = bloodGroup; }
    public void setGender(String gender) { this.gender = gender; }
    public void setState(String state) { this.state = state; }
    public void setDistrict(String district) { this.district = district; }
    public void setPreExistingConditions(String preExistingConditions) { this.preExistingConditions = preExistingConditions; }

    public Integer getId() { return id; }
    public String getPatientName() { return patientName; }
    public Integer getAge() { return age; }
    public String getBloodGroup() { return bloodGroup; }
    public String getGender() { return gender; }
    public String getState() { return state; }
    public String getDistrict() { return district; }
    public String getPreExistingConditions() { return preExistingConditions; }
}
