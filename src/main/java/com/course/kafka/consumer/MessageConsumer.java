package com.course.kafka.consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
public class MessageConsumer {

    private static final Logger log = LoggerFactory.getLogger(MessageConsumer.class);

    private final List<String> receivedMessages = Collections.synchronizedList(new ArrayList<>());

    @KafkaListener(
            topics = "${kafka.topic.name}",
            groupId = "${spring.kafka.consumer.group-id}"
    )
    public void consume(String message) {
        log.info("[{}] Message consumed on thread '{}': '{}'",
                threadType(),
                Thread.currentThread().getName(),
                message);
        receivedMessages.add(message);
    }

    public List<String> getReceivedMessages() {
        return Collections.unmodifiableList(receivedMessages);
    }

    /** Returns "virtual" or "platform" based on the current thread type. */
    private static String threadType() {
        return Thread.currentThread().isVirtual() ? "virtual" : "platform";
    }
}
