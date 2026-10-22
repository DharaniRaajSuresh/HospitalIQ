package com.hospitaliq.patientservice.entity;

import jakarta.persistence.*;


@Entity
@Table(name = "vaccine_history")
public class VaccineHistoryEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "patient_id", nullable = false)
    private Integer patientId;

    @Column(name = "vaccine_name", nullable = false)
    private String vaccineName;

    @Column(name = "dose_number")
    private Integer doseNumber;

    @Column(name = "vaccination_date")
    private String vaccinationDate;

    @Column(name = "hospital_name")
    private String hospitalName;

    @Column(name = "batch_number")
    private String batchNumber;

    @Column(name = "virus_name")
    private String virusName;

    private Double effectiveness;

    @Column(name = "created_at")
    private String createdAt;

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }
    public Integer getPatientId() { return patientId; }
    public void setPatientId(Integer patientId) { this.patientId = patientId; }
    public String getVaccineName() { return vaccineName; }
    public void setVaccineName(String vaccineName) { this.vaccineName = vaccineName; }
    public Integer getDoseNumber() { return doseNumber; }
    public void setDoseNumber(Integer doseNumber) { this.doseNumber = doseNumber; }
    public String getVaccinationDate() { return vaccinationDate; }
    public void setVaccinationDate(String vaccinationDate) { this.vaccinationDate = vaccinationDate; }
    public String getHospitalName() { return hospitalName; }
    public void setHospitalName(String hospitalName) { this.hospitalName = hospitalName; }
    public String getBatchNumber() { return batchNumber; }
    public void setBatchNumber(String batchNumber) { this.batchNumber = batchNumber; }
    public String getVirusName() { return virusName; }
    public void setVirusName(String virusName) { this.virusName = virusName; }
    public Double getEffectiveness() { return effectiveness; }
    public void setEffectiveness(Double effectiveness) { this.effectiveness = effectiveness; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
}
