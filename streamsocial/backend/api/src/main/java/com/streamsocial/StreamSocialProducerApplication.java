package com.streamsocial;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafka;

/**
 * StreamSocial Producer Application
 * REST API for publishing events to Kafka topics
 */
@SpringBootApplication
@EnableKafka
public class StreamSocialProducerApplication {

    public static void main(String[] args) {
        SpringApplication.run(StreamSocialProducerApplication.class, args);
    }
}
