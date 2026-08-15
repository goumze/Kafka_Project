package com.streamsocial;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafka;

/**
 * StreamSocial Consumer Application
 * Processes events from Kafka topics
 */
@SpringBootApplication
@EnableKafka
public class StreamSocialConsumerApplication {

    public static void main(String[] args) {
        SpringApplication.run(StreamSocialConsumerApplication.class, args);
    }
}
