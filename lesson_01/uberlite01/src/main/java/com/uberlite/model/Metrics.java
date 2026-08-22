package com.uberlite.model;

/**
 * Represents performance metrics for throughput and latency tracking.
 */
public record Metrics(
    long successCount,
    long failureCount,
    double p99LatencyMs,
    double throughput
) {}