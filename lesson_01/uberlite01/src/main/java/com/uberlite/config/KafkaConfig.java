package com.uberlite.config;

import com.uberlite.model.LocationEvent;
import com.uberlite.util.KafkaBootstrapResolver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.*;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;

import java.util.HashMap;
import java.util.Map;

/**
 * Kafka configuration for Spring Boot.
 * Sets up producers, consumers, and topics.
 */
@Configuration
@EnableKafka
public class KafkaConfig {
    private static final Logger log = LoggerFactory.getLogger(KafkaConfig.class);
    
    @Value("${spring.kafka.bootstrap-servers}")
    private String bootstrapServers;

    private String effectiveBootstrapServers() {
        return KafkaBootstrapResolver.resolveBootstrapServers(bootstrapServers);
    }

    /**
     * Kafka Admin configuration for topic management.
     */
    @Bean
    public KafkaAdmin kafkaAdmin() {
        Map<String, Object> configs = new HashMap<>();
        configs.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, effectiveBootstrapServers());
        return new KafkaAdmin(configs);
    }

    /**
     * Create location events topic if it doesn't exist.
     */
    @Bean
    public NewTopic locationEventsTopic() {
        return TopicBuilder.name("location-events")
            .partitions(12)
            .replicas(1)
            .config("retention.ms", "86400000") // 24 hours
            .config("compression.type", "gzip")
            .build();
    }

    /**
     * Producer factory for Location Events.
     */
    @Bean
    public ProducerFactory<String, LocationEvent> producerFactory() {
        Map<String, Object> configProps = new HashMap<>();
        configProps.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, effectiveBootstrapServers());
        configProps.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        configProps.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        configProps.put(ProducerConfig.ACKS_CONFIG, "all");
        configProps.put(ProducerConfig.RETRIES_CONFIG, 3);
        configProps.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "gzip");
        configProps.put(ProducerConfig.LINGER_MS_CONFIG, 10);
        configProps.put(ProducerConfig.BATCH_SIZE_CONFIG, 32768);
        configProps.put(ProducerConfig.BUFFER_MEMORY_CONFIG, 67108864); // 64MB
        
        return new DefaultKafkaProducerFactory<>(configProps);
    }

    /**
     * Kafka template for sending Location Events.
     */
    @Bean
    public KafkaTemplate<String, LocationEvent> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }

    /**
     * Consumer factory for Location Events.
     */
    @Bean
    public ConsumerFactory<String, LocationEvent> consumerFactory() {
        Map<String, Object> configProps = new HashMap<>();
        configProps.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, effectiveBootstrapServers());
        configProps.put(ConsumerConfig.GROUP_ID_CONFIG, "uberlite-lesson-01");
        configProps.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        configProps.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer.class);
        configProps.put(JsonDeserializer.VALUE_DEFAULT_TYPE, LocationEvent.class.getName());
        configProps.put(JsonDeserializer.TRUSTED_PACKAGES, "*");
        configProps.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        configProps.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
        configProps.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, 1000);
        configProps.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500);
        configProps.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, 30000);
        
        return new DefaultKafkaConsumerFactory<>(configProps);
    }

    /**
     * Kafka listener container factory for consuming Location Events.
     */
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, LocationEvent> kafkaListenerContainerFactory() {
        ConcurrentKafkaListenerContainerFactory<String, LocationEvent> factory =
            new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory());
        factory.setConcurrency(3);
        // Auto-commit is configured in the consumer factory, so we don't need to set AckMode explicitly
        factory.setBatchListener(false);
        
        return factory;
    }
}
