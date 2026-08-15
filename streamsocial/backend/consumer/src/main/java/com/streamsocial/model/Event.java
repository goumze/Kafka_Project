package com.streamsocial.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Event model representing a user action or system event
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Event {
    
    @JsonProperty("event_id")
    private String eventId;
    
    @JsonProperty("event_type")
    private String eventType;
    
    @JsonProperty("user_id")
    private String userId;
    
    @JsonProperty("timestamp")
    private LocalDateTime timestamp;
    
    @JsonProperty("payload")
    private String payload;
    
    @JsonProperty("source")
    private String source;
    
    /**
     * Factory method to create a new event with generated ID and current timestamp
     */
    public static Event create(String eventType, String userId, String payload, String source) {
        return Event.builder()
            .eventId(UUID.randomUUID().toString())
            .eventType(eventType)
            .userId(userId)
            .timestamp(LocalDateTime.now())
            .payload(payload)
            .source(source)
            .build();
    }
}
