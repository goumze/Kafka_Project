package com.streamsocial.config;

import com.streamsocial.model.Event;
import org.springframework.boot.autoconfigure.kafka.KafkaProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.listener.ContainerProperties;
import org.springframework.kafka.support.serializer.JsonDeserializer;

/**
 * Kafka configuration for the Consumer application
 */
@Configuration
@EnableKafka
public class KafkaConsumerConfig {
    
    /**
     * Configure consumer factory for Event deserialization
     */
    @Bean
    public ConsumerFactory<String, Event> consumerFactory(KafkaProperties kafkaProperties) {
        var props = kafkaProperties.buildConsumerProperties();
        
        // Configure JSON deserialization
        props.put(JsonDeserializer.VALUE_DEFAULT_TYPE, Event.class.getName());
        props.put(JsonDeserializer.TRUSTED_PACKAGES, "com.streamsocial.model");
        props.put(JsonDeserializer.USE_TYPE_INFO_HEADERS, "false");
        
        return new DefaultKafkaConsumerFactory<String, Event>(props);
    }
    
    /**
     * Configure concurrent listener container factory for batch processing
     */
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, Event> kafkaListenerContainerFactory(
            ConsumerFactory<String, Event> consumerFactory) {
        
        ConcurrentKafkaListenerContainerFactory<String, Event> factory = 
            new ConcurrentKafkaListenerContainerFactory<>();
        
        factory.setCommonErrorHandler(new org.springframework.kafka.listener.DefaultErrorHandler());
        factory.setConcurrency(3);
        factory.setBatchListener(true);
        factory.setConsumerFactory(consumerFactory);
        
        // Auto-commit offset handling
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.BATCH);
        
        return factory;
    }
}
