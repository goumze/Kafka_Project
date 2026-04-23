package com.course.kafka;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class KafkaProjectApplication {

    private static final Logger log = LoggerFactory.getLogger(KafkaProjectApplication.class);

    public static void main(String[] args) {
        SpringApplication.run(KafkaProjectApplication.class, args);
        log.info("=========================================================");
        log.info("  Kafka Project Application started successfully!");
        log.info("  Publish endpoint : POST http://localhost:8080/api/messages/publish");
        log.info("  Received messages: GET  http://localhost:8080/api/messages/received");
        log.info("  Health check     : GET  http://localhost:8080/actuator/health");
        log.info("=========================================================");
    }
}
