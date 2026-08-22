package com.uberlite.kafka;

import com.uberlite.model.LocationEvent;
import com.uberlite.model.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Kafka-based location event producer using Spring Kafka.
 * Demonstrates event-driven architecture for location tracking.
 */
@Service
public class KafkaLocationProducer {
    private static final Logger log = LoggerFactory.getLogger(KafkaLocationProducer.class);
    private static final String LOCATION_EVENTS_TOPIC = "location-events";
    
    private final KafkaTemplate<String, LocationEvent> kafkaTemplate;
    private final AtomicLong successCount = new AtomicLong();
    private final AtomicLong failureCount = new AtomicLong();
    private final List<Long> latencies = new ArrayList<>();

    public KafkaLocationProducer(KafkaTemplate<String, LocationEvent> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
        log.info("KafkaLocationProducer initialized with topic: {}", LOCATION_EVENTS_TOPIC);
    }

    /**
     * Sends a location event to Kafka.
     * Uses driver ID as the message key for partitioning by driver.
     */
    public void sendLocation(LocationEvent event) {
        var startTime = System.nanoTime();
        
        kafkaTemplate.send(LOCATION_EVENTS_TOPIC, event.driverId(), event)
            .whenComplete((sendResult, exception) -> {
                if (exception != null) {
                    failureCount.incrementAndGet();
                    log.debug("Failed to send location event for driver {}: {}", 
                        event.driverId(), exception.getMessage());
                } else {
                    var latencyNs = System.nanoTime() - startTime;
                    synchronized (latencies) {
                        latencies.add(latencyNs);
                    }
                    successCount.incrementAndGet();
                }
            });
    }

    /**
     * Returns current metrics for this producer.
     */
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
