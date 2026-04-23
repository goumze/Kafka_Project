package com.course.kafka.config;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.core.task.SimpleAsyncTaskExecutor;

import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

/**
 * Wires Java 21 virtual threads throughout the application:
 *
 * 1. Tomcat HTTP threads         → spring.threads.virtual.enabled=true (application.yaml)
 * 2. Kafka listener poll threads → SimpleAsyncTaskExecutor(virtualThreads=true)
 *                                  set on the ConcurrentKafkaListenerContainerFactory
 * 3. Producer send callbacks     → virtualThreadExecutor bean
 *                                  used by MessageProducer.whenCompleteAsync(...)
 */
@Configuration
public class VirtualThreadConfig {

    private static final Logger log = LoggerFactory.getLogger(VirtualThreadConfig.class);

    /**
     * A reusable virtual-thread-per-task executor for any async work in the app
     * (primarily producer send callbacks).
     */
    @Bean(name = "virtualThreadExecutor")
    public Executor virtualThreadExecutor() {
        return Executors.newVirtualThreadPerTaskExecutor();
    }

    /**
     * Customise the Kafka listener container factory so that every
     * @KafkaListener method is dispatched on a virtual thread.
     *
     * SimpleAsyncTaskExecutor with virtualThreads=true creates a new virtual
     * thread for each task submitted to it, matching exactly how
     * Executors.newVirtualThreadPerTaskExecutor() behaves but with
     * the Spring naming/lifecycle support built in.
     */
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory(
            ConsumerFactory<String, String> consumerFactory) {

        ConcurrentKafkaListenerContainerFactory<String, String> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);

        SimpleAsyncTaskExecutor executor = new SimpleAsyncTaskExecutor("kafka-vt-listener-");
        executor.setVirtualThreads(true);
        factory.getContainerProperties().setListenerTaskExecutor(executor);

        log.info("Kafka listener container factory configured with virtual-thread executor");
        return factory;
    }
}
