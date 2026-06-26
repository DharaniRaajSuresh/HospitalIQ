package com.hospitaliq.patientservice;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * HospitalIQ Patient Service — Spring Boot 3.4.4 microservice.
 *
 * <p>Handles patient CRUD, medical history (vaccines, travel, family), and
 * aggregate health statistics. Runs alongside the FastAPI ML inference service
 * in a polyglot microservices architecture.
 *
 * <p>{@code @EnableScheduling} activates {@code @Scheduled} tasks, e.g. the
 * 5-minute health-stats cache refresh in {@link service.HealthStatsService}.
 */
@SpringBootApplication
@EnableScheduling
public class PatientServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(PatientServiceApplication.class, args);
    }
}
