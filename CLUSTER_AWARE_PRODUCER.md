# Cluster-Aware Kafka Producer Implementation

## Overview

The enhanced `StreamSocialEventProducer` is a production-grade, cluster-aware Kafka producer designed to handle distributed event streaming in a multi-broker Kafka cluster environment. It provides robust reliability, performance optimization, and comprehensive monitoring capabilities.

## Key Features

### 1. **Cluster Metadata Discovery**
- Automatically discovers and caches cluster broker information
- Validates cluster connectivity on initialization
- Provides real-time cluster health monitoring

**Usage:**
```python
producer = StreamSocialEventProducer()
health = producer.check_cluster_health()
print(f"Cluster has {health['topics_available']} topics, {health['partitions']} partitions")
```

### 2. **Intelligent Partitioning Strategy**
- Uses consistent hashing on `user_id` to route related events to the same partition
- Guarantees ordering of events for each user (ordering guarantee)
- Distributes load evenly across all partitions

**How it works:**
- All events from `user_id='alice'` go to the same partition
- Ensures causality and temporal ordering for user-specific events
- Enables efficient consumer group rebalancing

### 3. **High Durability Configuration**
- **acks='all'**: Waits for acknowledgment from all in-sync replicas
- **min_insync_replicas=2**: Ensures at least 2 replicas acknowledge writes
- **replication_factor=3**: Replicates data across all brokers
- Prevents data loss even during broker failures

### 4. **Compression & Performance Optimization**
- **Compression Type**: Snappy (fast, good compression ratio)
- **Batch Size**: 16KB per batch
- **Linger Time**: 10ms to group messages
- **Max In-Flight Requests**: 5 concurrent requests for throughput

### 5. **Automatic Topic Management**
- Auto-creates topic with cluster-aware configuration
- Sets appropriate replication factor based on cluster size
- Configures retention policy (7 days)
- Validates topic existence on startup

### 6. **Retry Logic with Exponential Backoff**
- Automatic retries on transient failures
- Exponential backoff (100ms base) prevents broker overload
- Request timeout: 30 seconds for slow networks
- Async error callbacks for non-blocking error handling

### 7. **Resource Management**
- Context manager support for safe resource cleanup
- Proper flush and close operations
- Prevents resource leaks in production environments

**Usage:**
```python
with StreamSocialEventProducer() as producer:
    producer.publish_event(
        EventType.USER_LOGIN,
        user_id="alice",
        data={"ip": "192.168.1.1"}
    )
```

### 8. **Comprehensive Metrics Collection**
- Tracks messages sent/failed count
- Measures send latency (min, max, average)
- Monitors cluster health in real-time

**Usage:**
```python
metrics = producer.get_metrics()
print(f"Success rate: {metrics['messages_sent'] / (metrics['messages_sent'] + metrics['messages_failed'])}")
print(f"Avg latency: {metrics['avg_latency_ms']:.2f}ms")
```

### 9. **Batch Publishing**
- Publish multiple events efficiently
- Single flush operation for all events
- Partial failure handling

**Usage:**
```python
events = [
    {"event_type": "USER_LOGIN", "user_id": "alice", "data": {}},
    {"event_type": "USER_POST_CREATE", "user_id": "bob", "data": {}},
]
event_ids = producer.publish_batch(events)
```

## Configuration

### Default Configuration
```python
config = ClusterAwareProducerConfig(
    bootstrap_servers=['localhost:9091', 'localhost:9092', 'localhost:9093'],
    topic='streamsocial_events',
    partitions=3,
    replication_factor=3,
    min_insync_replicas=2,
    batch_size=16384,
    linger_ms=10,
    compression_type='snappy',
    acks='all',
    retries=3,
    retry_backoff_ms=100,
    request_timeout_ms=30000,
    max_in_flight_requests=5,
)
```

### Custom Configuration
```python
config = ClusterAwareProducerConfig(
    bootstrap_servers=['kafka-1:9092', 'kafka-2:9092', 'kafka-3:9092'],
    topic='my_custom_topic',
    partitions=6,
    batch_size=32768,
    linger_ms=20,
)
producer = StreamSocialEventProducer(config)
```

## Usage Examples

### Basic Event Publishing
```python
from producers.event_producer import StreamSocialEventProducer
from models.events import EventType

producer = StreamSocialEventProducer()

event_id = producer.publish_event(
    event_type=EventType.USER_LOGIN,
    user_id="alice",
    data={
        "ip": "192.168.1.1",
        "device": "mobile"
    }
)
print(f"Event published with ID: {event_id}")
```

### Async Publishing with Callback
```python
def on_send_success(metadata):
    print(f"Message sent to {metadata.topic} partition {metadata.partition}")

def on_send_error(exc):
    print(f"Error: {exc}")

producer.publish_event(
    event_type=EventType.USER_POST_CREATE,
    user_id="bob",
    data={"content": "Hello World"},
    callback=on_send_success
)
```

### Cluster Health Monitoring
```python
health = producer.check_cluster_health()
if health['status'] == 'healthy':
    print(f"Cluster healthy: {health['topics_available']} topics, {health['partitions']} partitions")
else:
    print(f"Cluster issues: {health['error']}")
```

### Metrics Collection
```python
metrics = producer.get_metrics()
print(f"""
Messages Sent: {metrics['messages_sent']}
Messages Failed: {metrics['messages_failed']}
Avg Latency: {metrics['avg_latency_ms']:.2f}ms
Max Latency: {metrics['max_latency_ms']:.2f}ms
""")
```

## Architecture Benefits

### 1. **Ordering Guarantees**
- User events maintain causality and temporal order
- Consumer can process events in the order they were produced
- Prevents race conditions in downstream processing

### 2. **Load Distribution**
- Partitions spread across 3 brokers
- Balanced write throughput
- Prevents hot partitions

### 3. **Fault Tolerance**
- Replicas on multiple brokers
- Automatic failover on broker crashes
- No data loss scenarios

### 4. **Performance**
- Compression reduces network bandwidth by ~50%
- Batching reduces broker load
- Async callbacks enable non-blocking operations

### 5. **Monitoring**
- Real-time health checks
- Latency tracking for SLO monitoring
- Success/failure metrics for alerting

## Docker Compose Integration

The implementation works seamlessly with the provided docker-compose.yml:
- 3 Kafka brokers in Kraft mode
- Auto-replication factor 3
- Min ISR (In-Sync Replicas) of 2
- Snappy compression enabled by default

## Error Handling

### Transient Errors
- Automatically retried with exponential backoff
- Max 3 retries (configurable)
- Suitable for network hiccups

### Permanent Errors
- Logged with full context
- Raised to caller for explicit handling
- Metrics updated for monitoring

```python
try:
    producer.publish_event(EventType.USER_LOGIN, "alice", {})
except KafkaError as e:
    logger.error(f"Failed to publish: {e}")
    # Alert monitoring system
```

## Best Practices

1. **Use Context Manager**
   ```python
   with StreamSocialEventProducer() as producer:
       producer.publish_event(...)
   ```

2. **Monitor Metrics Regularly**
   ```python
   metrics = producer.get_metrics()
   if metrics['messages_failed'] > threshold:
       alert()
   ```

3. **Check Cluster Health**
   ```python
   health = producer.check_cluster_health()
   if health['status'] != 'healthy':
       failover()
   ```

4. **Use Batch Publishing for Bulk Operations**
   ```python
   producer.publish_batch(events)  # More efficient than loop
   ```

5. **Reuse Producer Instance**
   ```python
   # Good: Reuse single instance
   producer = StreamSocialEventProducer()
   for event in events:
       producer.publish_event(...)
   
   # Bad: Create new instance per event (expensive)
   ```

## Performance Tuning

### For High Throughput
```python
config = ClusterAwareProducerConfig(
    batch_size=65536,  # Larger batches
    linger_ms=50,      # Wait longer for batches
    max_in_flight_requests=10,  # More concurrent requests
)
```

### For Low Latency
```python
config = ClusterAwareProducerConfig(
    batch_size=4096,   # Smaller batches
    linger_ms=1,       # Send immediately
    max_in_flight_requests=1,  # Sequential for ordering
)
```

## Troubleshooting

### Connection Refused
- Verify bootstrap servers are correct
- Check Kafka cluster is running: `docker-compose up -d`
- Verify network connectivity

### Slow Publishes
- Check `get_metrics()` for high latency
- Monitor broker logs
- Increase `batch_size` and `linger_ms`

### Failed Messages
- Check `messages_failed` in metrics
- Review error logs
- Verify cluster health with `check_cluster_health()`

## Migration from Old Producer

```python
# Old
producer = StreamSocialEventProducer()
producer.publish_event(EventType.USER_LOGIN, "alice", {})

# New (backward compatible)
producer = StreamSocialEventProducer()
producer.publish_event(EventType.USER_LOGIN, "alice", {})

# New features
health = producer.check_cluster_health()
metrics = producer.get_metrics()
```

The new implementation is backward compatible with existing code while providing additional features.

## References

- [Kafka Producer Tuning](https://kafka.apache.org/documentation/#producerconfigs)
- [Kraft Mode Documentation](https://kafka.apache.org/documentation/#kraft)
- [Python Kafka Client](https://kafka-python.readthedocs.io/)
