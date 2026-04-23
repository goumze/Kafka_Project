package com.course.kafka;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.test.context.EmbeddedKafka;

@SpringBootTest
@EmbeddedKafka(
        partitions = 1,
        brokerProperties = {
                "listeners=PLAINTEXT://localhost:9094",
                "port=9094"
        }
)
class KafkaProjectApplicationTests {

    @Test
    void contextLoads() {
    }
}
