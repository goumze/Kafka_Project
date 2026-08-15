package com.streamsocial.controller;

import com.streamsocial.model.Event;
import com.streamsocial.service.EventProducerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * REST Controller for event publishing
 */
@Slf4j
@RestController
@RequestMapping("/events")
@RequiredArgsConstructor
public class EventController {
    
    private final EventProducerService producerService;
    
    /**
     * Generate and publish test events in bulk
     * 
     * @param count Number of events to generate
     * @return Response with generated event count
     */
    @PostMapping("/bulk/generate")
    public ResponseEntity<Map<String, Object>> generateBulkEvents(
            @RequestParam(defaultValue = "100") int count) {
        
        log.info("Generating {} test events", count);
        
        try {
            for (int i = 0; i < count; i++) {
                // Rotate through event types
                String[] eventTypes = {"page_view", "click", "scroll", "purchase", "comment"};
                String eventType = eventTypes[i % eventTypes.length];
                
                // Rotate through topics/publishers
                String[] publishers = {"web", "mobile", "api", "admin"};
                String source = publishers[i % publishers.length];
                
                Event event = Event.create(
                    eventType,
                    "user_" + (i % 1000),
                    "{\"data\": \"test_payload_" + i + "\"}",
                    source
                );
                
                // Publish based on event type
                switch (eventType) {
                    case "purchase" -> producerService.publishContentInteraction(event);
                    case "comment" -> producerService.publishContentInteraction(event);
                    default -> producerService.publishUserAction(event);
                }
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("status", "success");
            response.put("events_generated", count);
            response.put("timestamp", System.currentTimeMillis());
            
            log.info("Successfully generated {} events", count);
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("Error generating bulk events: {}", e.getMessage(), e);
            
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("status", "error");
            errorResponse.put("message", e.getMessage());
            
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }
    
    /**
     * Publish a single event
     * 
     * @param event Event to publish
     * @return Response with published event details
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> publishEvent(@RequestBody Event event) {
        
        try {
            // Set generated ID if not provided
            if (event.getEventId() == null || event.getEventId().isEmpty()) {
                event.setEventId(UUID.randomUUID().toString());
            }
            
            // Determine topic based on event type
            if ("purchase".equals(event.getEventType()) || "comment".equals(event.getEventType())) {
                producerService.publishContentInteraction(event);
            } else {
                producerService.publishUserAction(event);
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("status", "published");
            response.put("event_id", event.getEventId());
            response.put("event_type", event.getEventType());
            response.put("timestamp", System.currentTimeMillis());
            
            log.info("Published event: {}", event.getEventId());
            return ResponseEntity.accepted().body(response);
            
        } catch (Exception e) {
            log.error("Error publishing event: {}", e.getMessage(), e);
            
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("status", "error");
            errorResponse.put("message", e.getMessage());
            
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }
    
    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        Map<String, String> response = new HashMap<>();
        response.put("status", "healthy");
        response.put("service", "streamsocial-api");
        return ResponseEntity.ok(response);
    }
}
