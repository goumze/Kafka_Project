# StreamSocial Kafka Topics & Partition Strategy Implementation

## Overview

Your StreamSocial application has been enhanced with a **dynamic, production-ready topic and partition strategy** based on the Hands On Kafka Day 3 article. The system now supports:

- **Multiple topics** with different partition strategies
- **Programmatic topic creation** with optimal configurations
- **Partition key strategies** for consistent message distribution
- **Hash-based partitioning** for even load balancing

---

## Topic Architecture

### 1. **user-actions Topic** (1000 Partitions)
**Purpose**: High-volume user-initiated actions with strict ordering requirements

**Partition Key**: `user_id`  
**Replication Factor**: 3  
**Compression**: gzip  
**Retention**: 7 days  

**Event Types**:
- `user_registration` - User signs up
- `user_login` / `user_logout` - Authentication events
- `user_profile_update` - Profile modifications
- `user_follow` / `user_unfollow` - Follow relationships
- `user_post_create` / `user_post_delete` / `user_post_edit` - Post management
- `user_comment_create` / `user_comment_delete` - Comments

**Why 1000 Partitions?**
```
Formula: Partitions = Target Throughput / Consumer Throughput
- Target: 50M requests/sec (StreamSocial scale)
- Single consumer handles: ~50K req/sec
- Required: 50M / 50K = 1000 partitions minimum
```

**Ordering Guarantee**: Each user's actions are strictly ordered within their partition

---

### 2. **content-interactions Topic** (500 Partitions)
**Purpose**: Content engagement events with relaxed ordering requirements

**Partition Key**: `content_id`  
**Replication Factor**: 3  
**Compression**: gzip  
**Retention**: 1 day  

**Event Types**:
- `content_like` / `content_unlike` - Like/unlike actions
- `content_comment` - Comments on content
- `content_share` - Sharing content
- `content_view` - View tracking
- `content_bookmark` - Bookmarking
- `content_analytics` - Analytics events

**Why 500 Partitions?**
```
- Optimized for analytics processing
- Reduces partition overhead vs. 1000
- Supports high-throughput content metrics
- Content-based distribution (not user-based)
```

**Relaxed Ordering**: Order within partition maintained, but cross-partition order undefined

---

### 3. **system-events Topic** (100 Partitions)
**Purpose**: System-level events with lower volume

**Partition Key**: `system_id` (default: "default")  
**Replication Factor**: 3  
**Compression**: gzip  
**Retention**: 3 days  

**Event Types**:
- `system_notification` - Notifications
- `system_alert` - System alerts
- `system_error` - Error events
- `system_health_check` - Health monitoring

---

## Partition Strategy Implementation

### Hash-Based Distribution

The system uses **SHA-256 based hashing** to ensure consistent, even distribution:

```python
# Partition calculation
hash_value = SHA256(f"{partition_key}").hex()
partition = int(hash_value, 16) % num_partitions
```

**Benefits**:
1. ✅ **Uniform Distribution**: Keys evenly distributed across all partitions
2. ✅ **Consistency**: Same key always maps to same partition
3. ✅ **No Hot Partitions**: Avoids sequential key patterns creating bottlenecks
4. ✅ **Scalability**: Works for billions of unique keys

### Anti-Patterns Avoided

❌ **Timestamp-based keys** → Creates hot partitions (all recent messages go to same partition)  
❌ **Sequential IDs** → Uneven distribution, early partitions overloaded  
✅ **User ID / Content ID** → Natural, high-cardinality keys with even distribution  

---

## Usage Examples

### Publishing Events

```python
from streamsocial.backend.producers.event_producer import StreamSocialEventProducer
from streamsocial.backend.models.events import EventType

# Initialize producer
producer = StreamSocialEventProducer()

# Create topics automatically
producer.ensure_topics_exist()

# Publish a user action (routed to user-actions topic)
producer.publish_user_action(
    event_type=EventType.USER_POST_CREATE,
    user_id="user_123",
    data={
        "post_id": "post_456",
        "content": "Hello StreamSocial!",
        "media_count": 2
    }
)

# Publish a content interaction (routed to content-interactions topic)
producer.publish_content_interaction(
    event_type=EventType.CONTENT_LIKE,
    user_id="user_123",
    content_id="post_456",  # Partition key for content-interactions
    data={
        "liked_at": "2024-07-28T10:30:00"
    }
)

# Get topic information
topic_info = producer.get_topic_info()
print(topic_info)
```

### Consuming Events

```python
from streamsocial.backend.consumers.event_consumer import StreamSocialEventConsumer
from streamsocial.backend.models.events import EventType

# Initialize consumer (automatically subscribes to all topics)
consumer = StreamSocialEventConsumer(group_id='analytics_service')

# Register event handlers
def handle_like_event(event):
    print(f"Content liked: {event['data']}")

consumer.register_handler(EventType.CONTENT_LIKE, handle_like_event)

# Start consuming
consumer.start_consuming()
```

### Partition Calculation

```python
from streamsocial.backend.config.partition_strategy import PartitionStrategy

strategy = PartitionStrategy()

# Get partition for a user action
partition = strategy.get_partition_for_user_action(user_id="user_123")
print(f"User action partition: {partition}")  # 0-999

# Get partition for content interaction
partition = strategy.get_partition_for_content_interaction(content_id="post_456")
print(f"Content interaction partition: {partition}")  # 0-499
```

---

## Configuration Details

### Topic Configuration File

Located: `streamsocial/backend/config/topic_config.py`

Key classes:
- **TopicConfig**: Dataclass defining topic parameters
- **StreamSocialTopicManager**: Central manager with all topic definitions
- **EVENT_TO_TOPIC_MAP**: Maps event types to topics

### Partition Strategy File

Located: `streamsocial/backend/config/partition_strategy.py`

Key classes:
- **PartitionStrategy**: Implements hash-based partitioning
- Topic-specific methods: `get_partition_for_user_action()`, `get_partition_for_content_interaction()`

---

## Partition Balancing & Monitoring

### Expected Load Distribution

For **1000 partitions** with even key distribution:
```
Total users: 50M (example)
Avg messages per partition: 50M / 1000 = 50K messages
Throughput per partition: ~50K req/s / 1000 = 50 msg/sec
```

### Identifying Hot Partitions

Monitor these metrics:
- **Lag per partition**: Should be similar across all partitions
- **Throughput variance**: Should stay within 20% of average
- **Message size**: Similar distribution across partitions

### Consumer Group Scaling

**Recommended scaling**:
- Start: `partition_count / 2` consumers
- Monitor lag per partition
- Scale up when lag exceeds threshold
- Max: 1 consumer per partition

Example for user-actions (1000 partitions):
```
Start: 500 consumers
Monitor: Adjust based on lag
Max: 1000 consumers (1 per partition)
```

---

## Testing & Validation

### Verify Topic Creation

```bash
# Inside container
kafka-topics.sh --list --bootstrap-server localhost:9092

# Expected output:
# user-actions
# content-interactions
# system-events
```

### Check Partition Distribution

```bash
# Describe topics
kafka-topics.sh --describe --bootstrap-server localhost:9092

# Check partition leader distribution
kafka-topics.sh --describe --under-replicated-partitions --bootstrap-server localhost:9092
```

### Verify Message Distribution

```python
# Test script to verify even distribution
from streamsocial.backend.config.partition_strategy import PartitionStrategy

strategy = PartitionStrategy()
partition_counts = {}

# Generate sample user IDs and check distribution
for i in range(10000):
    user_id = f"user_{i}"
    partition = strategy.get_partition_for_user_action(user_id)
    partition_counts[partition] = partition_counts.get(partition, 0) + 1

# Check variance
import statistics
counts = list(partition_counts.values())
mean = statistics.mean(counts)
variance = statistics.variance(counts)
std_dev = statistics.stdev(counts)

print(f"Mean: {mean:.2f}")
print(f"Variance: {variance:.2f}")
print(f"Std Dev: {std_dev:.2f}")
print(f"Distribution: {'Even' if std_dev < mean * 0.1 else 'Uneven'}")
```

---

## Performance Optimizations in Producer

The enhanced producer includes:

1. **Batching**: `batch_size=16384` (16KB) + `linger_ms=10`
2. **Compression**: gzip compression reduces network bandwidth
3. **Replication**: `acks='all'` ensures all replicas receive messages
4. **Connection Pooling**: Automatically managed by KafkaProducer
5. **Error Handling**: Automatic retries (max 10 attempts)

### Throughput Expectations

With current settings:
- **Single producer**: ~100K-500K msg/sec (depends on message size)
- **Multiple producers**: Linear scaling up to network limits
- **Total cluster capacity**: Designed for 50M+ req/sec across multiple brokers

---

## Architecture Diagram

```
Event Types → Topic Router → Topics with Partitions → Consumers
                ↓
User Actions (1000p)     ← Ordered by user_id
                          ← Even distribution
Content Interactions (500p) ← Ordered by content_id
                          ← Analytics optimized
System Events (100p)      ← System notifications
                          ← Lower volume
```

---

## Next Steps

1. ✅ **Test topic creation**: `producer.ensure_topics_exist()`
2. ✅ **Publish sample events**: Use examples above
3. ✅ **Verify distribution**: Run validation scripts
4. ✅ **Monitor performance**: Track lag and throughput per partition
5. ✅ **Scale consumers**: Add more consumers based on lag

---

## References

- **Hands On Kafka Day 3**: https://handsonkafka.substack.com/p/day-3-topics-and-partitions-strategy
- **Kafka Partitioning**: https://kafka.apache.org/documentation/#bestpractices_partitioning
- **Consumer Groups**: https://kafka.apache.org/documentation/#consumerconfigs

---

## Summary of Enhancements

| Component | Before | After |
|-----------|--------|-------|
| Topics | 1 hardcoded | 3 configured topics |
| Partitions | 10 (hardcoded) | 1000 + 500 + 100 (dynamic) |
| Partition Strategy | Basic | Hash-based, event-aware |
| Topic Config | None | Centralized, extensible |
| Consumer | Single topic | Multi-topic support |
| Event Types | 9 | 15+ with routing |
| Logging | Minimal | Detailed per operation |

Your StreamSocial platform is now ready to scale to production levels! 🚀
