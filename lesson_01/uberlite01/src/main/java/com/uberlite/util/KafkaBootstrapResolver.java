package com.uberlite.util;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class KafkaBootstrapResolver {

    public static final String DEFAULT_LOCAL_BOOTSTRAP = "localhost:9094,localhost:9096,localhost:9098";

    private KafkaBootstrapResolver() {
    }

    public static String resolveBootstrapServers(String configuredValue) {
        return resolveBootstrapServers(configuredValue, isRunningInDockerContainer());
    }

    static String resolveBootstrapServers(String configuredValue, boolean runningInDocker) {
        if (configuredValue == null || configuredValue.isBlank()) {
            return DEFAULT_LOCAL_BOOTSTRAP;
        }

        if (runningInDocker) {
            return configuredValue.trim();
        }

        List<String> resolved = new ArrayList<>();
        String[] entries = configuredValue.split(",");

        for (String entry : entries) {
            String broker = entry.trim();
            if (broker.isEmpty()) {
                continue;
            }

            int colonIndex = broker.lastIndexOf(':');
            if (colonIndex > 0) {
                String host = broker.substring(0, colonIndex);
                String port = broker.substring(colonIndex + 1);
                if (host.toLowerCase(Locale.ROOT).startsWith("kafka")) {
                    Integer brokerId = parseBrokerId(host);
                    if (brokerId != null) {
                        resolved.add("localhost:" + (9092 + (brokerId * 2)));
                        continue;
                    }
                }
            }

            resolved.add(broker);
        }

        if (resolved.isEmpty()) {
            return DEFAULT_LOCAL_BOOTSTRAP;
        }

        return String.join(",", resolved);
    }

    private static Integer parseBrokerId(String host) {
        String digits = host.replaceAll("\\D", "");
        if (digits.isEmpty()) {
            return null;
        }

        try {
            return Integer.parseInt(digits);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static boolean isRunningInDockerContainer() {
        String forceValue = System.getProperty("uberlite.running.in.docker");
        if (forceValue != null) {
            return Boolean.parseBoolean(forceValue);
        }

        String envValue = System.getenv("IS_DOCKER");
        if (envValue != null) {
            return Boolean.parseBoolean(envValue);
        }

        try {
            String cgroup = Files.readString(Path.of("/proc/1/cgroup"));
            if (cgroup.contains("docker") || cgroup.contains("containerd") || cgroup.contains("kubepods")) {
                return true;
            }
        } catch (IOException | UnsupportedOperationException e) {
            return false;
        }

        return false;
    }
}
