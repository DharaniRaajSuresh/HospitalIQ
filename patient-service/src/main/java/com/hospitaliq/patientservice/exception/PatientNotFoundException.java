package com.hospitaliq.patientservice.exception;

public class PatientNotFoundException extends RuntimeException {
    private final Integer patientId;

    public PatientNotFoundException(Integer patientId) {
        super("Patient not found: " + patientId);
        this.patientId = patientId;
    }

    public Integer getPatientId() { return patientId; }
}
