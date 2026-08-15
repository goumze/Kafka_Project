# StreamSocial Java Spring Boot Refactoring Guide

## Overview
This Docker Compose setup has been refactored to work with **Java Spring Boot** applications using **Spring Kafka** for Kafka integration. The architecture includes:

- **3-broker Kafka cluster** (KRaft mode - no Zookeeper)
- **Kafka UI** for cluster monitoring
- **Spring Boot API service** (REST endpoints for event management)
- **Spring Boot Consumer service** (scalable workers processing Kafka events)

## Project Structure

```
streamsocial/
├── Dockerfile                    # docker-compose.yml (refactored for Java)
├── backend/
│   ├── api/                     # Spring Boot API application
│   │   ├── pom.xml             # Maven configuration
│   │   ├── Dockerfile          # Multi-stage build for API
│   │   └── src/main/
│   │       ├── java/com/streamsocial/
│   │       │   ├── StreamSocialApiApplication.java
│   │       │   ├── controller/EventController.java
│   │       │   ├── service/EventProducerService.java
│   │       │   └── model/Event.java
│   │       └── resources/application.yml
│   │
│   └── consumer/                 # Spring Boot Consumer application
│       ├── pom.xml             # Maven configuration
│       ├── Dockerfile          # Multi-stage build for Consumer
│       └── src/main/
│           ├── java/com/streamsocial/
│           │   ├── StreamSocialConsumerApplication.java
│           │   ├── service/EventConsumerService.java
│           │   ├── model/Event.java
│           │   └── handler/EventHandler.java
│           └── resources/application.yml
```

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Maven 3.9+** (for local development)
- **Java 21 JDK** (for local development)

## Quick Start

### 1. Create Project Structure

```bash
# Create Maven project structure for API
mkdir -p streamsocial/backend/api/src/main/{java/com/streamsocial,resources}
mkdir -p streamsocial/backend/api/src/test/java/com/streamsocial

# Create Maven project structure for Consumer
mkdir -p streamsocial/backend/consumer/src/main/{java/com/streamsocial,resources}
mkdir -p streamsocial/backend/consumer/src/test/java/com/streamsocial
```

### 2. Create Main Application Classes

#### API Application (`streamsocial/backend/api/src/main/java/com/streamsocial/StreamSocialApiApplication.java`)

```java
package com.streamsocial;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class StreamSocialApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(StreamSocialApiApplication.class, args);
    }
}
```

#### API Controller (`streamsocial/backend/api/src/main/java/com/streamsocial/controller/EventController.java`)

```java
package com.streamsocial.controller;

import com.streamsocial.model.Event;
import com.streamsocial.service.EventProducerService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

@RestController
@RequestMapping("/events")
@RequiredArgsConstructor
public class EventController {
    
    private final EventProducerService producerService;
    
    @PostMapping
    public ResponseEntity<Event> createEvent(@RequestBody Event event) {
        event.setId(UUID.randomUUID().toString());
        producerService.sendEvent(event);
        return ResponseEntity.ok(event);
    }
    
    @PostMapping("/bulk/generate")
    public ResponseEntity<String> generateBulkEvents(
            @RequestParam(defaultValue = "100") int count) {
        List<Event> events = IntStream.range(0, count)
            .mapToObj(i -> Event.builder()
                .id(UUID.randomUUID().toString())
                .userId("user_" + (i % 50))
                .eventType("action")
                .timestamp(System.currentTimeMillis())
                .data("Bulk event #" + i)
                .build())
            .collect(Collectors.toList());
        
        events.forEach(producerService::sendEvent);
        return ResponseEntity.ok("Generated " + count + " events");
    }
    
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("API is running");
    }
}
```

#### Event Model (`streamsocial/backend/api/src/main/java/com/streamsocial/model/Event.java`)

```java
package com.streamsocial.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Event {
    private String id;
    private String userId;
    private String eventType;
    private long timestamp;
    private String data;
}
```

#### Event Producer Service (`streamsocial/backend/api/src/main/java/com/streamsocial/service/EventProducerService.java`)

```java
package com.streamsocial.service;

import com.streamsocial.model.Event;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
@Slf4j
public class EventProducerService {
    
    private final KafkaTemplate<String, Event> kafkaTemplate;
    private static final String TOPIC = "user-actions";
    
    public void sendEvent(Event event) {
        Message<Event> message = MessageBuilder
            .withPayload(event)
            .setHeader(KafkaHeaders.TOPIC, TOPIC)
            .setHeader(KafkaHeaders.MESSAGE_KEY, event.getUserId())
            .build();
        
        kafkaTemplate.send(message);
        log.debug("Event sent: {}", event.getId());
    }
}
```

### 3. Consumer Application Classes

#### Consumer Application (`streamsocial/backend/consumer/src/main/java/com/streamsocial/StreamSocialConsumerApplication.java`)

```java
package com.streamsocial;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafka;

@SpringBootApplication
@EnableKafka
public class StreamSocialConsumerApplication {
    public static void main(String[] args) {
        SpringApplication.run(StreamSocialConsumerApplication.class, args);
    }
}
```

#### Event Consumer Service (`streamsocial/backend/consumer/src/main/java/com/streamsocial/service/EventConsumerService.java`)

```java
package com.streamsocial.service;

import com.streamsocial.model.Event;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@Slf4j
public class EventConsumerService {
    
    @KafkaListener(
        topics = "user-actions",
        groupId = "${spring.kafka.consumer.group-id}"
    )
    public void consumeEvent(@Payload Event event) {
        log.info("Event consumed: userId={}, eventType={}, timestamp={}", 
            event.getUserId(), event.getEventType(), event.getTimestamp());
        
        // Simulate processing delay
        try {
            Thread.sleep(5);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
    
    @KafkaListener(
        topics = "user-actions",
        groupId = "${spring.kafka.consumer.group-id}",
        containerFactory = "batchFactory"
    )
    public void consumeBatch(List<Event> events) {
        log.info("Batch processing {} events", events.size());
        events.forEach(event -> 
            log.debug("Processing: {}", event.getId())
        );
    }
}
```

## Running with Docker Compose

### Start the Stack

```bash
# From project root
docker compose up -d --build
```

### Scale Consumer Workers

```bash
# Scale to 3 consumer instances
docker compose up -d --scale kafka-consumer=3
```

### Monitor Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f backend-api
docker compose logs -f kafka-consumer
```

### Access Services

- **Kafka UI**: http://localhost:8080
- **API Health**: http://localhost:8000/actuator/health
- **API Metrics**: http://localhost:8000/actuator/metrics

### Test the API

```bash
# Generate bulk events
curl -X POST http://localhost:8000/api/events/bulk/generate?count=100

# Create single event
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user_123",
    "eventType": "click",
    "timestamp": '$(date +%s)'000,
    "data": "test event"
  }'
```

### Shutdown

```bash
docker compose down
docker compose down -v  # Also remove volumes
```

## Environment Variables

The docker-compose.yml defines these variables (all can be overridden):

### Kafka Configuration
- `SPRING_KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `SPRING_KAFKA_CONSUMER_GROUP_ID`: Consumer group identifier
- `SPRING_KAFKA_PRODUCER_ACKS`: Producer acknowledgment level
- `SPRING_KAFKA_PRODUCER_COMPRESSION_TYPE`: Compression algorithm

### Java/Spring Boot
- `JAVA_TOOL_OPTIONS`: JVM tuning parameters
- `SPRING_PROFILES_ACTIVE`: Active Spring profiles (docker, consumer)
- `SERVER_PORT`: API service port
- `LOGGING_LEVEL_ROOT`: Root logging level

## Kafka Topics

The consumer expects these topics (auto-create enabled):

| Topic | Partitions | Replication |
|-------|-----------|-------------|
| user-actions | 24 | 3 |
| content-interactions | 12 | 3 |
| system-events | 6 | 3 |

## Development

### Local Build

```bash
cd streamsocial/backend/api
mvn clean package

cd ../consumer
mvn clean package
```

### Run Locally (requires Kafka running)

```bash
# Terminal 1: API
java -jar backend/api/target/streamsocial-api-1.0.0.jar

# Terminal 2: Consumer
java -jar backend/consumer/target/streamsocial-consumer-1.0.0.jar
```

## Troubleshooting

### Consumer lag not reducing
- Check if consumer is running: `docker compose ps`
- View consumer logs: `docker compose logs -f kafka-consumer`
- Verify Kafka connectivity in Kafka UI

### API not responding
- Check health endpoint: `curl http://localhost:8000/actuator/health`
- View logs: `docker compose logs -f backend-api`
- Ensure Kafka cluster is healthy

### Out of memory errors
- Adjust JVM settings in `JAVA_TOOL_OPTIONS` environment variable
- Modify in docker-compose.yml or add `.env` file

## Notes

- Uses **KRaft** (Kafka Raft) - no Zookeeper required
- **Java 21** with Alpine Linux for smaller images
- **Multi-stage Docker builds** for optimized image sizes
- **Spring Kafka** provides abstraction over native Kafka clients
- Consumer is **horizontally scalable** (max = # of topic partitions)

For more details on Spring Kafka, see: https://spring.io/projects/spring-kafka
