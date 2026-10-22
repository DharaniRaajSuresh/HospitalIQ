package com.hospitaliq.patientservice.util;

/**
 * Utility class to handle pagination logic and input adaptation.
 * 
 * <p>Why this exists: Controllers should be extremely "thin" and only route data.
 * If we need to adapt legacy frontend parameters (like supporting both 'skip' and 'offset'),
 * that logic belongs in a utility or adapter layer, not directly in the controller method.
 */
public final class PaginationUtil {

    private PaginationUtil() {
        throw new UnsupportedOperationException("Utility class");
    }

    /**
     * Resolves the skip value, falling back to an 'offset' string if provided.
     * This ensures frontend compatibility without bloating the controller.
     *
     * @param skip   The standard skip parameter (parsed by Spring)
     * @param offset The legacy offset parameter (string)
     * @return The resolved skip integer
     */
    public static int resolveSkip(int skip, String offset) {
        if (offset != null && skip == 0) {
            try {
                return Integer.parseInt(offset);
            } catch (NumberFormatException ignored) {
                // If it's malformed, ignore and just use the default skip
            }
        }
        return skip;
    }
}
