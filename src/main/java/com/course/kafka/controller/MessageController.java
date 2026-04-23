package com.course.kafka.controller;

import com.course.kafka.consumer.MessageConsumer;
import com.course.kafka.producer.MessageProducer;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/messages")
public class MessageController {

    private final MessageProducer producer;
    private final MessageConsumer consumer;

    public MessageController(MessageProducer producer, MessageConsumer consumer) {
        this.producer = producer;
        this.consumer = consumer;
    }

    /**
     * Publish a message to Kafka.
     *
     * Request body (JSON):
     *   { "message": "Hello Kafka!" }
     *   { "key": "order-1", "message": "Hello Kafka!" }   <- optional key for partition routing
     */
    @PostMapping("/publish")
    public ResponseEntity<Map<String, String>> publish(@RequestBody Map<String, String> request) {
        String message = request.get("message");
        if (message == null || message.isBlank()) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "Field 'message' is required and cannot be blank"));
        }
        String key = request.get("key");
        if (key != null && !key.isBlank()) {
            producer.sendMessage(key, message);
        } else {
            producer.sendMessage(message);
        }
        return ResponseEntity.ok(Map.of(
                "status", "published",
                "message", message
        ));
    }

    /**
     * Retrieve all messages consumed so far during this session.
     */
    @GetMapping("/received")
    public ResponseEntity<List<String>> getReceivedMessages() {
        return ResponseEntity.ok(consumer.getReceivedMessages());
    }
}
