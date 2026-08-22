package com.uberlite.rest;

import com.uberlite.model.DriverLocation;
import com.uberlite.model.Metrics;
import com.uberlite.postgres.PostgresLocationUpdater;
import com.uberlite.kafka.KafkaLocationProducer;
import com.uberlite.service.LocationStateService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * REST API Controller for location queries and metrics.
 * Provides dashboard endpoints for real-time monitoring.
 */
@RestController
@RequestMapping("/locations")
@CrossOrigin(origins = "*")
public class LocationController {
    private static final Logger log = LoggerFactory.getLogger(LocationController.class);
    
    private final LocationStateService locationStateService;
    private final PostgresLocationUpdater postgresUpdater;
    private final KafkaLocationProducer kafkaProducer;
    
    @Value("${app.mode:both}")
    private String appMode;

    public LocationController(LocationStateService locationStateService, 
                             PostgresLocationUpdater postgresUpdater,
                             KafkaLocationProducer kafkaProducer) {
        this.locationStateService = locationStateService;
        this.postgresUpdater = postgresUpdater;
        this.kafkaProducer = kafkaProducer;
    }

    /**
     * Get current location of a specific driver.
     */
    @GetMapping("/{driverId}")
    public ResponseEntity<DriverLocation> getDriverLocation(@PathVariable String driverId) {
        try {
            var location = locationStateService.getDriverLocation(driverId);
            if (location != null) {
                return ResponseEntity.ok(location);
            } else {
                return ResponseEntity.notFound().build();
            }
        } catch (Exception e) {
            log.error("Error fetching location for driver {}: {}", driverId, e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get all driver locations (paginated).
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getAllLocations(
        @RequestParam(defaultValue = "0") int offset,
        @RequestParam(defaultValue = "100") int limit
    ) {
        try {
            var locations = locationStateService.getAllDriverLocations(offset, limit);
            var count = locationStateService.getDriverCount();
            
            return ResponseEntity.ok(Map.of(
                "total", count,
                "offset", offset,
                "limit", limit,
                "locations", locations
            ));
        } catch (Exception e) {
            log.error("Error fetching all locations: {}", e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get current metrics for PostgreSQL path.
     */
    @GetMapping("/metrics/postgres")
    public ResponseEntity<Metrics> getPostgresMetrics() {
        try {
            var metrics = postgresUpdater.getMetrics();
            return ResponseEntity.ok(metrics);
        } catch (Exception e) {
            log.error("Error fetching postgres metrics: {}", e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get current metrics for Kafka path.
     */
    @GetMapping("/metrics/kafka")
    public ResponseEntity<Metrics> getKafkaMetrics() {
        try {
            var metrics = kafkaProducer.getMetrics();
            return ResponseEntity.ok(metrics);
        } catch (Exception e) {
            log.error("Error fetching kafka metrics: {}", e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get combined health/status information.
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> getHealth() {
        try {
            var postgresMetrics = postgresUpdater.getMetrics();
            var kafkaMetrics = kafkaProducer.getMetrics();
            
            return ResponseEntity.ok(Map.of(
                "status", "UP",
                "mode", appMode,
                "postgres", postgresMetrics,
                "kafka", kafkaMetrics
            ));
        } catch (Exception e) {
            return ResponseEntity.ok(Map.of(
                "status", "DEGRADED",
                "error", e.getMessage()
            ));
        }
    }

    /**
     * Search for drivers in a geographic region.
     */
    @GetMapping("/search")
    public ResponseEntity<Map<String, Object>> searchDriversByRegion(
        @RequestParam double minLat,
        @RequestParam double maxLat,
        @RequestParam double minLon,
        @RequestParam double maxLon
    ) {
        try {
            var drivers = locationStateService.findDriversByRegion(minLat, maxLat, minLon, maxLon);
            return ResponseEntity.ok(Map.of(
                "count", drivers.size(),
                "drivers", drivers
            ));
        } catch (Exception e) {
            log.error("Error searching drivers: {}", e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }
}
