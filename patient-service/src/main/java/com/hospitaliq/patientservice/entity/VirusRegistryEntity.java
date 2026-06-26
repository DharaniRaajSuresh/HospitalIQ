package com.hospitaliq.patientservice.entity;

import jakarta.persistence.*;


@Entity
@Table(name = "virus_registry")
public class VirusRegistryEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "virus_name", nullable = false, unique = true)
    private String virusName;

    @Column(name = "fatality_rate")
    private Double fatalityRate;

    @Column(name = "reproductive_rate")
    private Double reproductiveRate;

    @Column(name = "incubation_period_days")
    private Integer incubationPeriodDays;

    @Column(name = "transmission_mode")
    private String transmissionMode;

    @Column(name = "vaccine_available")
    private Boolean vaccineAvailable;

    @Column(name = "vaccine_effectiveness")
    private Double vaccineEffectiveness;

    @Column(name = "treatment_available")
    private Boolean treatmentAvailable;

    private String notes;

    @Column(name = "created_at")
    private String createdAt;

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }
    public String getVirusName() { return virusName; }
    public void setVirusName(String virusName) { this.virusName = virusName; }
    public Double getFatalityRate() { return fatalityRate; }
    public void setFatalityRate(Double fatalityRate) { this.fatalityRate = fatalityRate; }
    public Double getReproductiveRate() { return reproductiveRate; }
    public void setReproductiveRate(Double reproductiveRate) { this.reproductiveRate = reproductiveRate; }
    public Integer getIncubationPeriodDays() { return incubationPeriodDays; }
    public void setIncubationPeriodDays(Integer incubationPeriodDays) { this.incubationPeriodDays = incubationPeriodDays; }
    public String getTransmissionMode() { return transmissionMode; }
    public void setTransmissionMode(String transmissionMode) { this.transmissionMode = transmissionMode; }
    public Boolean getVaccineAvailable() { return vaccineAvailable; }
    public void setVaccineAvailable(Boolean vaccineAvailable) { this.vaccineAvailable = vaccineAvailable; }
    public Double getVaccineEffectiveness() { return vaccineEffectiveness; }
    public void setVaccineEffectiveness(Double vaccineEffectiveness) { this.vaccineEffectiveness = vaccineEffectiveness; }
    public Boolean getTreatmentAvailable() { return treatmentAvailable; }
    public void setTreatmentAvailable(Boolean treatmentAvailable) { this.treatmentAvailable = treatmentAvailable; }
    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
}
