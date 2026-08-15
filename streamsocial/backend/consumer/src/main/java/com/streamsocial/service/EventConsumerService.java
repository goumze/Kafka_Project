package com.streamsocial.service;

import com.streamsocial.model.Event;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.annotation.TopicPartition;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Consumer service for processing events from Kafka topics
 */
@Slf4j
@Service
public class EventConsumerService {
    
    private final AtomicLong processedCount = new AtomicLong(0);
    
    /**
     * Listen for user action events from all partitions
     */
    @KafkaListener(
        topics = "user-actions",
        groupId = "${spring.kafka.consumer.group-id}",
        concurrency = "${spring.kafka.listener.concurrency:3}"
    )
    public void consumeUserActions(List<Event> events) {
        processEvents("user-actions", events);
    }
    
    /**
     * Listen for content interaction events from all partitions
     */
    @KafkaListener(
        topics = "content-interactions",
        groupId = "${spring.kafka.consumer.group-id}",
        concurrency = "${spring.kafka.listener.concurrency:3}"
    )
    public void consumeContentInteractions(List<Event> events) {
        processEvents("content-interactions", events);
    }
    
    /**
     * Listen for system events from all partitions
     */
    @KafkaListener(
        topics = "system-events",
        groupId = "${spring.kafka.consumer.group-id}",
        concurrency = "${spring.kafka.listener.concurrency:3}"
    )
    public void consumeSystemEvents(List<Event> events) {
        processEvents("system-events", events);
    }
    
    /**
     * Process a batch of events
     */
    private void processEvents(String topic, List<Event> events) {
        if (events == null || events.isEmpty()) {
            return;
        }
        
        for (Event event : events) {
            try {
                // Simulate processing delay (configurable)
                long delay = Long.parseLong(System.getenv("CONSUMER_PROCESSING_DELAY_MS") != null 
                    ? System.getenv("CONSUMER_PROCESSING_DELAY_MS") 
                    : "5");
                
                if (delay > 0) {
                    Thread.sleep(delay);
                }
                
                // Process the event
                log.debug("Processing event from topic '{}': eventId={}, eventType={}, userId={}", 
                    topic, event.getEventId(), event.getEventType(), event.getUserId());
                
                processedCount.incrementAndGet();
                
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("Processing interrupted for event: {}", event.getEventId());
            } catch (Exception e) {
                log.error("Error processing event {}: {}", event.getEventId(), e.getMessage(), e);
            }
        }
        
        // Log periodically
        long total = processedCount.get();
        if (total % 1000 == 0) {
            log.info("Total events processed: {}", total);
        }
    }
    
    /**
     * Get the count of processed events
     */
    public long getProcessedCount() {
        return processedCount.get();
    }
}
