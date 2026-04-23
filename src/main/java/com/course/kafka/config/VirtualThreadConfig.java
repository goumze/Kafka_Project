package com.course.kafka.config;

import org.springframework.beans.BeansException;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.SimpleAsyncTaskExecutor;
import org.springframework.core.task.VirtualThreadTaskExecutor;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;

import java.util.concurrent.Executor;

/**
 * Configures the application to use Java 21 Virtual Threads across all
 * concurrency boundaries:
 *
 * <ul>
 *   <li>Tomcat HTTP threads — enabled via {@code spring.threads.virtual.enabled=true}
 *       in application.yaml (no code change required).</li>
 *   <li>Kafka consumer listener threads — the auto-configured
 *       {@code kafkaListenerContainerFactory} is post-processed to attach a
 *       {@link SimpleAsyncTaskExecutor} (with virtual threads enabled) as its
 *       listener task executor.</li>
 *   <li>Kafka producer send-callback threads — the shared {@code virtualThreadExecutor}
 *       bean used in {@link com.course.kafka.producer.MessageProducer}.</li>
 * </ul>
 */
@Configuration
public class VirtualThreadConfig {

    /**
     * Shared virtual-thread executor for one-off tasks (e.g. producer callbacks).
     * Thread names follow the pattern {@code producer-vt-0}, {@code producer-vt-1}, …
     */
    @Bean
    public Executor virtualThreadExecutor() {
        return new VirtualThreadTaskExecutor("producer-vt-");
    }

    /**
     * Post-processes the auto-configured {@code kafkaListenerContainerFactory} to
     * attach a virtual-thread-backed {@link SimpleAsyncTaskExecutor} as the listener
     * task executor. {@code SimpleAsyncTaskExecutor} implements the
     * {@code AsyncListenableTaskExecutor} interface expected by Spring Kafka 3.1,
     * while {@code setVirtualThreads(true)} ensures each task runs on a JVM virtual
     * thread on Java 21+.
     */
    @Bean
    public static BeanPostProcessor kafkaListenerVirtualThreadCustomizer() {
        return new BeanPostProcessor() {
            @Override
            public Object postProcessAfterInitialization(Object bean, String beanName) throws BeansException {
                if ("kafkaListenerContainerFactory".equals(beanName)
                        && bean instanceof ConcurrentKafkaListenerContainerFactory<?, ?> factory) {
                    var executor = new SimpleAsyncTaskExecutor("kafka-listener-vt-");
                    executor.setVirtualThreads(true);
                    factory.getContainerProperties().setListenerTaskExecutor(executor);
                }
                return bean;
            }
        };
    }
}
