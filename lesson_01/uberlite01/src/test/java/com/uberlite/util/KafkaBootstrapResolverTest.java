package com.uberlite.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class KafkaBootstrapResolverTest {

    @Test
    void resolvesDockerKafkaAliasesToLocalhostPorts() {
        String input = "kafka1:9092,kafka2:9092,kafka3:9092";

        assertEquals("localhost:9094,localhost:9096,localhost:9098",
                KafkaBootstrapResolver.resolveBootstrapServers(input));
    }

    @Test
    void keepsExplicitExternalHostsUntouched() {
        String input = "localhost:9094,localhost:9096,localhost:9098";

        assertEquals(input, KafkaBootstrapResolver.resolveBootstrapServers(input));
    }

    @Test
    void fallsBackToDefaultLocalBootstrapWhenBlank() {
        assertEquals("localhost:9094,localhost:9096,localhost:9098",
                KafkaBootstrapResolver.resolveBootstrapServers("   "));
    }
}
