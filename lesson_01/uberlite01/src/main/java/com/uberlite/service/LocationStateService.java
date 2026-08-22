package com.uberlite.service;

import com.uberlite.model.DriverLocation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * Service for querying driver location state from PostgreSQL.
 * Provides various query methods for the REST API.
 */
@Service
public class LocationStateService {
    private static final Logger log = LoggerFactory.getLogger(LocationStateService.class);
    private final DataSource dataSource;

    public LocationStateService(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    /**
     * Get the current location of a specific driver.
     */
    public DriverLocation getDriverLocation(String driverId) {
        try (var conn = dataSource.getConnection();
             var stmt = conn.prepareStatement(
                 "SELECT driver_id, latitude, longitude, updated_at FROM drivers WHERE driver_id = ?"
             )) {
            
            stmt.setString(1, driverId);
            var rs = stmt.executeQuery();
            
            if (rs.next()) {
                return new DriverLocation(
                    rs.getString("driver_id"),
                    rs.getDouble("latitude"),
                    rs.getDouble("longitude"),
                    rs.getLong("updated_at")
                );
            }
        } catch (SQLException e) {
            log.error("Error fetching location for driver {}: {}", driverId, e.getMessage());
        }
        return null;
    }

    /**
     * Get all driver locations with pagination.
     */
    public List<DriverLocation> getAllDriverLocations(int offset, int limit) {
        var locations = new ArrayList<DriverLocation>();
        try (var conn = dataSource.getConnection();
             var stmt = conn.prepareStatement(
                 "SELECT driver_id, latitude, longitude, updated_at FROM drivers ORDER BY updated_at DESC LIMIT ? OFFSET ?"
             )) {
            
            stmt.setInt(1, limit);
            stmt.setInt(2, offset);
            var rs = stmt.executeQuery();
            
            while (rs.next()) {
                locations.add(new DriverLocation(
                    rs.getString("driver_id"),
                    rs.getDouble("latitude"),
                    rs.getDouble("longitude"),
                    rs.getLong("updated_at")
                ));
            }
        } catch (SQLException e) {
            log.error("Error fetching all locations: {}", e.getMessage());
        }
        return locations;
    }

    /**
     * Get total count of drivers.
     */
    public long getDriverCount() {
        try (var conn = dataSource.getConnection();
             var stmt = conn.createStatement()) {
            
            var rs = stmt.executeQuery("SELECT COUNT(*) as count FROM drivers");
            if (rs.next()) {
                return rs.getLong("count");
            }
        } catch (SQLException e) {
            log.error("Error fetching driver count: {}", e.getMessage());
        }
        return 0;
    }

    /**
     * Find drivers in a geographic region.
     */
    public List<DriverLocation> findDriversByRegion(double minLat, double maxLat, double minLon, double maxLon) {
        var locations = new ArrayList<DriverLocation>();
        try (var conn = dataSource.getConnection();
             var stmt = conn.prepareStatement(
                 "SELECT driver_id, latitude, longitude, updated_at FROM drivers " +
                 "WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? " +
                 "ORDER BY updated_at DESC LIMIT 1000"
             )) {
            
            stmt.setDouble(1, minLat);
            stmt.setDouble(2, maxLat);
            stmt.setDouble(3, minLon);
            stmt.setDouble(4, maxLon);
            var rs = stmt.executeQuery();
            
            while (rs.next()) {
                locations.add(new DriverLocation(
                    rs.getString("driver_id"),
                    rs.getDouble("latitude"),
                    rs.getDouble("longitude"),
                    rs.getLong("updated_at")
                ));
            }
        } catch (SQLException e) {
            log.error("Error searching drivers in region: {}", e.getMessage());
        }
        return locations;
    }

    /**
     * Get recently updated drivers (for real-time monitoring).
     */
    public List<DriverLocation> getRecentlyUpdatedDrivers(int limit) {
        var locations = new ArrayList<DriverLocation>();
        try (var conn = dataSource.getConnection();
             var stmt = conn.prepareStatement(
                 "SELECT driver_id, latitude, longitude, updated_at FROM drivers " +
                 "ORDER BY updated_at DESC LIMIT ?"
             )) {
            
            stmt.setInt(1, limit);
            var rs = stmt.executeQuery();
            
            while (rs.next()) {
                locations.add(new DriverLocation(
                    rs.getString("driver_id"),
                    rs.getDouble("latitude"),
                    rs.getDouble("longitude"),
                    rs.getLong("updated_at")
                ));
            }
        } catch (SQLException e) {
            log.error("Error fetching recently updated drivers: {}", e.getMessage());
        }
        return locations;
    }
}
