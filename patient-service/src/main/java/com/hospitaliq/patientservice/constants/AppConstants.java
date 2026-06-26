package com.hospitaliq.patientservice.constants;

/**
 * Global application constants.
 * 
 * <p>Centralizing hardcoded values (like pagination defaults or configuration keys)
 * into a constants file improves readability and ensures consistency across the application.
 * This is a common enterprise pattern to avoid "magic strings" in controllers.
 */
public final class AppConstants {

    // Prevent instantiation of utility/constant classes
    private AppConstants() {
        throw new UnsupportedOperationException("This is a constant class and cannot be instantiated");
    }

    public static final String DEFAULT_PAGE_SKIP = "0";
    public static final String DEFAULT_PAGE_LIMIT = "50";
}
