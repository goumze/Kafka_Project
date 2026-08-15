package com.streamsocial.config;

import com.streamsocial.model.Event;
import org.springframework.boot.autoconfigure.kafka.KafkaProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.JsonSerializer;

/**
 * Kafka configuration for the Producer application
 */
@Configuration
public class KafkaProducerConfig {
    
    /**
     * Configure KafkaTemplate for publishing Event objects
     */
    @Bean
    public KafkaTemplate<String, Event> kafkaTemplate(KafkaProperties kafkaProperties) {
        ProducerFactory<String, Event> producerFactory = 
            new DefaultKafkaProducerFactory<>(kafkaProperties.buildProducerProperties());
        
        KafkaTemplate<String, Event> template = new KafkaTemplate<>(producerFactory);
        template.setDefaultTopic("user-actions");
        
        return template;
    }
}
