package com.hospitaliq.patientservice.dto;

import java.util.List;

public class PaginatedResponse<T> {

    private List<T> patients;
    private long total;
    private int skip;
    private int limit;

    public PaginatedResponse(List<T> patients, long total, int skip, int limit) {
        this.patients = patients;
        this.total = total;
        this.skip = skip;
        this.limit = limit;
    }

    public List<T> getPatients() { return patients; }
    public long getTotal() { return total; }
    public int getSkip() { return skip; }
    public int getLimit() { return limit; }
}
