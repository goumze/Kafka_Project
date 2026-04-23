# Kafka Project — Spring Boot + Apache Kafka (KRaft)

A plug-and-play single Docker container that bundles:

- **Apache Kafka 3.9.0** running in **KRaft mode** (no ZooKeeper)
- **Spring Boot 3.3** REST application for publishing and consuming Kafka messages

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

### Option B — Plain Docker

```bash
# Build
docker build -t kafka-spring-app .

# Run
docker run -p 8080:8080 -p 9092:9092 kafka-spring-app
```

The container is healthy once both Kafka and the Spring Boot app are ready (allow ~60–90 seconds on first run).

---

## REST API

### Publish a message

```bash
curl -X POST http://localhost:8080/api/messages/publish \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello Kafka!"}'
```

Publish with an explicit partition key:

```bash
curl -X POST http://localhost:8080/api/messages/publish \
     -H "Content-Type: application/json" \
     -d '{"key": "order-1", "message": "Order placed"}'
```

### Retrieve consumed messages

```bash
curl http://localhost:8080/api/messages/received
```

### Health check

```bash
curl http://localhost:8080/actuator/health
```

---

## Environment Variables

| Variable                  | Default       | Description                          |
|---------------------------|---------------|--------------------------------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka bootstrap address           |
| `KAFKA_TOPIC_NAME`        | `messages`    | Topic used for publish / consume     |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Docker Container                    │
│                                                      │
│  ┌─────────────────────┐   ┌──────────────────────┐  │
│  │  Apache Kafka 3.9.0 │   │  Spring Boot App     │  │
│  │  KRaft (no ZK)      │◄──│  Producer  Consumer  │  │
│  │  Port: 9092         │   │  REST API  Port:8080 │  │
│  └─────────────────────┘   └──────────────────────┘  │
│                                                      │
│  start.sh: Kafka starts first → topic created →      │
│            Spring Boot starts                        │
└──────────────────────────────────────────────────────┘
```

## Project Structure

```
.
├── Dockerfile                        # Multi-stage build
├── docker-compose.yml                # Compose shortcut
├── start.sh                          # Container entrypoint
├── pom.xml                           # Maven project
├── config/
│   └── kraft/
│       └── server.properties         # Kafka KRaft config
└── src/main/java/com/course/kafka/
    ├── KafkaProjectApplication.java
    ├── config/
    │   └── KafkaTopicConfig.java      # Auto-creates the topic
    ├── producer/
    │   └── MessageProducer.java
    ├── consumer/
    │   └── MessageConsumer.java
    └── controller/
        └── MessageController.java
```
