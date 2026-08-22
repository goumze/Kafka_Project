package com.uberlite.kafka;

import com.uberlite.model.LocationEvent;
import com.uberlite.postgres.PostgresLocationUpdater;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;

/**
 * Kafka consumer/listener for location events.
 * Processes location events and updates the PostgreSQL state store.
 */
@Service
public class LocationEventListener {
    private static final Logger log = LoggerFactory.getLogger(LocationEventListener.class);
    private static final String LOCATION_EVENTS_TOPIC = "location-events";
    private static final String CONSUMER_GROUP = "uberlite-lesson-01";
    
    private final PostgresLocationUpdater postgresUpdater;

    public LocationEventListener(PostgresLocationUpdater postgresUpdater) {
        this.postgresUpdater = postgresUpdater;
        log.info("LocationEventListener initialized");
    }

    /**
     * Listens to location events from Kafka and updates PostgreSQL.
     * Processes events with topic and offset tracking.
     */
    @KafkaListener(
        topics = LOCATION_EVENTS_TOPIC,
        groupId = CONSUMER_GROUP,
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void processLocationEvent(
        @Payload LocationEvent event,
        @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
        @Header(name = "kafka_receivedPartitionId", required = false) Integer partition,
        @Header(KafkaHeaders.OFFSET) long offset
    ) {
        try {
            postgresUpdater.updateLocation(event);
            log.debug("Processed location event for driver {} from partition {} offset {}", 
                event.driverId(), partition != null ? partition : "unknown", offset);
        } catch (Exception e) {
            log.error("Error processing location event for driver {}: {}", 
                event.driverId(), e.getMessage());
            // In production, you might want to send to a DLQ here
        }
    }
}
