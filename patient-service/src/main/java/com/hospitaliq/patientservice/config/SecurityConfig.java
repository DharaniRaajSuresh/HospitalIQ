package com.hospitaliq.patientservice.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import jakarta.servlet.http.HttpServletResponse;
import java.util.Arrays;
import java.util.List;


/**
 * Spring Security configuration for the Patient Service.
 *
 * <p>Security model:
 * <ul>
 *   <li>Stateless JWT authentication via {@link JwtAuthFilter} (Bearer header or httpOnly cookie)</li>
 *   <li>All {@code /api/**} endpoints require a valid JWT — enforced by Spring Security
 *       AND by the filter. Defense-in-depth: both layers must pass.</li>
 *   <li>Public endpoints ({@code /actuator/health}, {@code /api/v1/patients/viruses/list})
 *       are explicitly permitted without auth for discovery/liveness purposes.</li>
 * </ul>
 *
 * <p>CORS origins are injected via the {@code CORS_ALLOWED_ORIGINS} environment variable
 * (comma-separated), defaulting to localhost for development.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    /**
     * Comma-separated list of allowed origins, e.g. {@code http://localhost:8510,https://app.example.com}.
     * Injected from {@code CORS_ALLOWED_ORIGINS} env var; defaults to localhost for development.
     */
    @Value("${cors.allowed-origins:http://localhost:8510,http://127.0.0.1:8510}")
    private String allowedOriginsRaw;

    public SecurityConfig(JwtAuthFilter jwtAuthFilter) {
        this.jwtAuthFilter = jwtAuthFilter;
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // Disable Spring's anonymous authentication filter — with a stateless JWT API, we don't
            // want anonymous tokens in the SecurityContext. Unauthenticated requests should get 401,
            // not 403 (which is what Spring returns when AnonymousAuthenticationToken hits authenticated()).
            .anonymous(anon -> anon.disable())
            // Return 401 (not 403) for requests that reach protected endpoints without authentication.
            .exceptionHandling(ex -> ex.authenticationEntryPoint(
                (request, response, authException) -> {
                    response.setContentType("application/json");
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.getWriter().write("{\"detail\":\"Not authenticated\",\"status\":401}");
                }
            ))
            .authorizeHttpRequests(auth -> auth
                // Publicly accessible endpoints (liveness probe + virus registry for pre-login UI)
                .requestMatchers(
                    "/actuator/health",
                    "/api/v1/patients/viruses/list",
                    "/api/v1/patients/stats",
                    "/api/v1/health-stats"    // aggregate dashboard stats — public for landing page
                ).permitAll()
                // All other requests MUST be authenticated — enforced by Spring Security
                // in addition to the JwtAuthFilter. Double layer of defence.
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();

    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();

        // Parse comma-separated origins from environment variable
        List<String> origins = Arrays.stream(allowedOriginsRaw.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
        config.setAllowedOrigins(origins);

        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}

