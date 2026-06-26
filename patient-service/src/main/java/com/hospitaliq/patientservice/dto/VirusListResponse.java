package com.hospitaliq.patientservice.dto;

import com.hospitaliq.patientservice.entity.VirusRegistryEntity;
import java.util.List;
import java.util.stream.Collectors;

public class VirusListResponse {

    private List<VirusRecord> viruses;

    public VirusListResponse(List<VirusRegistryEntity> entities) {
        this.viruses = entities.stream().map(VirusRecord::fromEntity).collect(Collectors.toList());
    }

    public List<VirusRecord> getViruses() { return viruses; }

    public static class VirusRecord {
        private Integer id;
        private String virusName;
        private Double fatalityRate;
        private Double reproductiveRate;
        private Integer incubationPeriodDays;
        private String transmissionMode;
        private Boolean vaccineAvailable;
        private Double vaccineEffectiveness;
        private Boolean treatmentAvailable;
        private String notes;

        static VirusRecord fromEntity(VirusRegistryEntity e) {
            VirusRecord r = new VirusRecord();
            r.id = e.getId();
            r.virusName = e.getVirusName();
            r.fatalityRate = e.getFatalityRate();
            r.reproductiveRate = e.getReproductiveRate();
            r.incubationPeriodDays = e.getIncubationPeriodDays();
            r.transmissionMode = e.getTransmissionMode();
            r.vaccineAvailable = e.getVaccineAvailable();
            r.vaccineEffectiveness = e.getVaccineEffectiveness();
            r.treatmentAvailable = e.getTreatmentAvailable();
            r.notes = e.getNotes();
            return r;
        }

        public Integer getId() { return id; }
        public String getVirusName() { return virusName; }
        public Double getFatalityRate() { return fatalityRate; }
        public Double getReproductiveRate() { return reproductiveRate; }
        public Integer getIncubationPeriodDays() { return incubationPeriodDays; }
        public String getTransmissionMode() { return transmissionMode; }
        public Boolean getVaccineAvailable() { return vaccineAvailable; }
        public Double getVaccineEffectiveness() { return vaccineEffectiveness; }
        public Boolean getTreatmentAvailable() { return treatmentAvailable; }
        public String getNotes() { return notes; }
    }
}
