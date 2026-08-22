package com.uberlite.postgres;

import com.uberlite.model.LocationEvent;
import com.uberlite.model.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * PostgreSQL-based location update service.
 * Demonstrates monolithic approach with direct database writes.
 */
@Service
public class PostgresLocationUpdater {
    private static final Logger log = LoggerFactory.getLogger(PostgresLocationUpdater.class);
    private final DataSource dataSource;
    private final AtomicLong successCount = new AtomicLong();
    private final AtomicLong failureCount = new AtomicLong();
    private final List<Long> latencies = new ArrayList<>();

    public PostgresLocationUpdater(DataSource dataSource) {
        this.dataSource = dataSource;
        initSchema();
    }

    private void initSchema() {
        try (var conn = dataSource.getConnection();
             var stmt = conn.createStatement()) {
            
            stmt.execute("""
                CREATE TABLE IF NOT EXISTS drivers (
                    driver_id VARCHAR(64) PRIMARY KEY,
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    updated_at BIGINT
                )
            """);
            
            stmt.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON drivers(updated_at)");
            log.info("Database schema initialized successfully");
            
        } catch (SQLException e) {
            log.warn("Error initializing schema (may already exist): {}", e.getMessage());
        }
    }

    public void updateLocation(LocationEvent event) {
        var startTime = System.nanoTime();
        try (var conn = dataSource.getConnection();
             var stmt = conn.prepareStatement(
                 "INSERT INTO drivers (driver_id, latitude, longitude, updated_at) " +
                 "VALUES (?, ?, ?, ?) " +
                 "ON CONFLICT (driver_id) DO UPDATE SET " +
                 "latitude = EXCLUDED.latitude, " +
                 "longitude = EXCLUDED.longitude, " +
                 "updated_at = EXCLUDED.updated_at"
             )) {
            
            stmt.setString(1, event.driverId());
            stmt.setDouble(2, event.latitude());
            stmt.setDouble(3, event.longitude());
            stmt.setLong(4, event.timestamp());
            stmt.executeUpdate();
            
            var latencyNs = System.nanoTime() - startTime;
            synchronized (latencies) {
                latencies.add(latencyNs);
            }
            successCount.incrementAndGet();
            
        } catch (SQLException e) {
            failureCount.incrementAndGet();
            log.debug("Failed to update location for driver {}: {}", event.driverId(), e.getMessage());
        }
    }

    public Metrics getMetrics() {
        List<Long> snapshot;
        synchronized (latencies) {
            snapshot = new ArrayList<>(latencies);
            latencies.clear();
        }
        
        if (snapshot.isEmpty()) {
            return new Metrics(successCount.get(), failureCount.get(), 0.0, 0.0);
        }
        
        snapshot.sort(Long::compareTo);
        var p99Index = (int) (snapshot.size() * 0.99);
        var p99LatencyMs = snapshot.get(p99Index) / 1_000_000.0;
        var throughput = snapshot.size() / 10.0; // 10 second window
        
        return new Metrics(successCount.get(), failureCount.get(), p99LatencyMs, throughput);
    }
}