package com.uberlite.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Represents the current location state of a driver.
 * This is the snapshot stored in PostgreSQL after processing location events.
 */
public record DriverLocation(
    @JsonProperty("driver_id") String driverId,
    @JsonProperty("latitude") double latitude,
    @JsonProperty("longitude") double longitude,
    @JsonProperty("updated_at") long updatedAt
) {
    @JsonCreator
    public DriverLocation {}
}