package com.streamsocial.service;

import com.streamsocial.model.Event;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;

/**
 * Producer service for publishing events to Kafka topics
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EventProducerService {
    
    private final KafkaTemplate<String, Event> kafkaTemplate;
    
    private static final String USER_ACTIONS_TOPIC = "user-actions";
    private static final String CONTENT_INTERACTIONS_TOPIC = "content-interactions";
    private static final String SYSTEM_EVENTS_TOPIC = "system-events";
    
    /**
     * Publish a user action event
     */
    public void publishUserAction(Event event) {
        publishToTopic(USER_ACTIONS_TOPIC, event);
    }
    
    /**
     * Publish a content interaction event
     */
    public void publishContentInteraction(Event event) {
        publishToTopic(CONTENT_INTERACTIONS_TOPIC, event);
    }
    
    /**
     * Publish a system event
     */
    public void publishSystemEvent(Event event) {
        publishToTopic(SYSTEM_EVENTS_TOPIC, event);
    }
    
    /**
     * Generic publish method for any topic
     */
    private void publishToTopic(String topic, Event event) {
        try {
            Message<Event> message = MessageBuilder
                .withPayload(event)
                .setHeader(KafkaHeaders.TOPIC, topic)
                .setHeader("kafka_messageKey", event.getUserId())
                .build();
            
            kafkaTemplate.send(message);
            log.debug("Published event to topic '{}': eventId={}, eventType={}", 
                topic, event.getEventId(), event.getEventType());
        } catch (Exception e) {
            log.error("Failed to publish event to topic '{}': {}", topic, e.getMessage(), e);
            throw new RuntimeException("Failed to publish event", e);
        }
    }
}
