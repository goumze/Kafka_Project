package com.uberlite;

import com.uberlite.kafka.KafkaLocationProducer;
import com.uberlite.loadgen.LoadGenerator;
import com.uberlite.postgres.PostgresLocationUpdater;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.stereotype.Component;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Spring Boot Application for Uber-Lite Lesson 01.
 * Demonstrates comparison between monolithic (PostgreSQL) and event-driven (Kafka) architectures.
 */
@SpringBootApplication
public class UberliteLesson01Application {
    private static final Logger log = LoggerFactory.getLogger(UberliteLesson01Application.class);

    public static void main(String[] args) {
        SpringApplication.run(UberliteLesson01Application.class, args);
    }
}

/**
 * Command line runner to initialize load generation based on configured mode.
 */
@Component
class LoadGeneratorRunner implements CommandLineRunner {
    private static final Logger log = LoggerFactory.getLogger(LoadGeneratorRunner.class);
    
    @Value("${app.mode:both}")
    private String mode;
    
    @Value("${app.load-generator.num-drivers:1000}")
    private int numDrivers;
    
    @Value("${app.load-generator.events-per-second:3000}")
    private int eventsPerSecond;
    
    @Value("${app.metrics.report-interval-seconds:10}")
    private long reportIntervalSeconds;
    
    @Autowired
    private PostgresLocationUpdater postgresUpdater;
    
    @Autowired
    private KafkaLocationProducer kafkaProducer;

    @Override
    public void run(String... args) throws Exception {
        log.info("🚀 Uber-Lite Lesson 01: Monolith vs Event-Driven Architecture");
        log.info("Mode: {}", mode);
        log.info("Drivers: {} | Events/sec: {}", numDrivers, eventsPerSecond);
        log.info("============================================================");
        
        var executor = Executors.newScheduledThreadPool(4);
        
        if ("postgres".equals(mode) || "both".equals(mode)) {
            runPostgresTest(executor);
        }
        
        if ("kafka".equals(mode) || "both".equals(mode)) {
            runKafkaTest(executor);
        }
        
        log.info("✅ Application started successfully. REST API available at http://localhost:8080/api");
        log.info("📊 Metrics endpoints:");
        log.info("   - Postgres: http://localhost:8080/api/locations/metrics/postgres");
        log.info("   - Kafka:    http://localhost:8080/api/locations/metrics/kafka");
        log.info("   - Health:   http://localhost:8080/api/locations/health");
    }
    
    private void runPostgresTest(ScheduledExecutorService executor) {
        log.info("📊 Starting PostgreSQL Mode (Monolithic)...");
        
        var loadGen = new LoadGenerator(numDrivers, eventsPerSecond);
        loadGen.start(postgresUpdater::updateLocation);
        
        executor.scheduleAtFixedRate(() -> {
            var metrics = postgresUpdater.getMetrics();
            log.info("[PostgreSQL] Throughput: {}/s | P99: {:.2f}ms | Success: {} | Failures: {}",
                String.format("%.0f", metrics.throughput()),
                metrics.p99LatencyMs(),
                metrics.successCount(),
                metrics.failureCount());
        }, reportIntervalSeconds, reportIntervalSeconds, TimeUnit.SECONDS);
    }
    
    private void runKafkaTest(ScheduledExecutorService executor) {
        log.info("📊 Starting Kafka Mode (Event-Driven)...");
        
        var loadGen = new LoadGenerator(numDrivers, eventsPerSecond);
        loadGen.start(kafkaProducer::sendLocation);
        
        executor.scheduleAtFixedRate(() -> {
            var metrics = kafkaProducer.getMetrics();
            log.info("[Kafka] Throughput: {}/s | P99: {:.2f}ms | Success: {} | Failures: {}",
                String.format("%.0f", metrics.throughput()),
                metrics.p99LatencyMs(),
                metrics.successCount(),
                metrics.failureCount());
        }, reportIntervalSeconds, reportIntervalSeconds, TimeUnit.SECONDS);
    }
}