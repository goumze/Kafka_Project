package com.course.kafka.producer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

@Service
public class MessageProducer {

    private static final Logger log = LoggerFactory.getLogger(MessageProducer.class);

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final Executor virtualThreadExecutor;

    @Value("${kafka.topic.name}")
    private String topicName;

    public MessageProducer(KafkaTemplate<String, String> kafkaTemplate,
                           @Qualifier("virtualThreadExecutor") Executor virtualThreadExecutor) {
        this.kafkaTemplate = kafkaTemplate;
        this.virtualThreadExecutor = virtualThreadExecutor;
    }

    public void sendMessage(String message) {
        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(topicName, message);
        // whenCompleteAsync dispatches the callback onto a new virtual thread
        future.whenCompleteAsync((result, ex) -> {
            if (ex == null) {
                log.info("[{}] Message published: '{}' | topic='{}' partition={} offset={}",
                        threadType(),
                        message,
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
            } else {
                log.error("[{}] Failed to publish message: '{}'", threadType(), message, ex);
            }
        }, virtualThreadExecutor);
    }

    public void sendMessage(String key, String message) {
        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(topicName, key, message);
        future.whenCompleteAsync((result, ex) -> {
            if (ex == null) {
                log.info("[{}] Message published: key='{}' value='{}' | topic='{}' partition={} offset={}",
                        threadType(),
                        key,
                        message,
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
            } else {
                log.error("[{}] Failed to publish message: key='{}' value='{}'", threadType(), key, message, ex);
            }
        }, virtualThreadExecutor);
    }

    /** Returns "virtual" or "platform" based on the current thread type. */
    private static String threadType() {
        return Thread.currentThread().isVirtual() ? "virtual" : "platform";
    }
}
