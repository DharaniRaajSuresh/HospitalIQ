package com.hospitaliq.patientservice.entity;

import jakarta.persistence.*;


@Entity
@Table(name = "family_history")
public class FamilyHistoryEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "patient_id", nullable = false)
    private Integer patientId;

    private String relationship;

    private String condition;

    @Column(name = "age_at_diagnosis")
    private Integer ageAtDiagnosis;

    @Column(name = "is_deceased")
    private Boolean isDeceased;

    @Column(name = "created_at")
    private String createdAt;

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }
    public Integer getPatientId() { return patientId; }
    public void setPatientId(Integer patientId) { this.patientId = patientId; }
    public String getRelationship() { return relationship; }
    public void setRelationship(String relationship) { this.relationship = relationship; }
    public String getCondition() { return condition; }
    public void setCondition(String condition) { this.condition = condition; }
    public Integer getAgeAtDiagnosis() { return ageAtDiagnosis; }
    public void setAgeAtDiagnosis(Integer ageAtDiagnosis) { this.ageAtDiagnosis = ageAtDiagnosis; }
    public Boolean getIsDeceased() { return isDeceased; }
    public void setIsDeceased(Boolean isDeceased) { this.isDeceased = isDeceased; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
}
