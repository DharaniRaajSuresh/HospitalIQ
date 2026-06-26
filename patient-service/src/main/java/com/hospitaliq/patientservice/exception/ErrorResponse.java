package com.hospitaliq.patientservice.exception;

/**
 * Legacy ErrorResponse — kept for backward compat with test imports.
 * The canonical implementation is {@link GlobalExceptionHandler.ErrorResponse} (a Java record).
 * This class will be removed once all tests reference the nested record directly.
 */
public class ErrorResponse {
    private final String detail;

    public ErrorResponse(String detail) {
        this.detail = detail;
    }

    public String getDetail() { return detail; }
}
