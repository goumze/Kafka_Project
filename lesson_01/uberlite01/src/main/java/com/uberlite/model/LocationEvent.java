package com.uberlite.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Represents a location event from a driver.
 * Used as payload for Kafka messages and internal events.
 */
public record LocationEvent(
    @JsonProperty("driver_id") String driverId,
    @JsonProperty("latitude") double latitude,
    @JsonProperty("longitude") double longitude,
    @JsonProperty("timestamp") long timestamp
) {
    @JsonCreator
    public LocationEvent {}
}