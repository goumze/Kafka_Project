# StreamSocial Kafka Integration - Complete Setup Guide

## Architecture Overview

```
FastAPI Backend (Port 8000)
    ↓
    ├── Produces Events → Kafka Topic (streamsocial_events)
    └── Consumer Thread (Background)
            ↓
            Processes Events
            ↓
            Stores in Memory & Provides Stats
```

## Components

### 1. **Event Producer** (`producers/event_producer.py`)
- Sends events to Kafka topic `streamsocial_events`
- Serializes events as JSON
- Ensures all replicas acknowledge (acks='all')
- Bootstrap servers: `localhost:9092`, `localhost:9093`, `localhost:9094`

### 2. **Event Consumer** (`consumers/consumer_runner.py`)
- Consumes events from Kafka topic
- Processes events with registered handlers
- Stores last 1000 events in memory
- Tracks total events processed
- Consumer group: `streamsocial_event_consumers`

### 3. **FastAPI Backend** (`main.py`)
- Starts consumer in background thread on startup
- Provides REST endpoints for:
  - Registering users
  - Viewing recent events
  - Consumer statistics
  - Starting/stopping consumer

---

## Quick Start Guide

### Prerequisites
```bash
cd /workspaces/Kafka_Project
docker-compose up -d  # If not already running
```

### Step 1: Start the FastAPI Backend
The backend automatically starts the consumer in the background:
```bash
python streamsocial/backend/main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
Starting Kafka consumer in background...
```

### Step 2: Send Test Events (in another terminal)
```bash
cd /workspaces/Kafka_Project
python streamsocial/backend/test_producer.py
```

Output:
```
============================================================
StreamSocial Event Producer Test
============================================================

Sending 5 sample events to Kafka...

Event 1:
  Type: user_registration
  User ID: <uuid>
  Data: {...}
  ✓ Sent successfully
...
```

### Step 3: Verify Consumer Processing
Check consumer stats via API:
```bash
curl http://localhost:8000/consumer/stats
```

Response:
```json
{
  "status": "running",
  "running": true,
  "total_events_processed": 5,
  "events_in_memory": 5,
  "recent_events": [...]
}
```

---

## API Endpoints

### Health Check
```bash
GET http://localhost:8000/health
```

### Get Consumer Statistics
```bash
GET http://localhost:8000/consumer/stats
```

### Get Recent Events (Processed by Consumer)
```bash
GET http://localhost:8000/events/recent
```

### Start Consumer
```bash
POST http://localhost:8000/consumer/start
```

### Stop Consumer
```bash
POST http://localhost:8000/consumer/stop
```

### Register User
```bash
POST http://localhost:8000/events/user/register
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "source": "web"
}
```

---

## Kafka CLI Commands (for debugging)

### List all topics
```bash
docker exec kafka-broker-1 kafka-topics --bootstrap-server kafka-1:29092 --list
```

### Describe streamsocial_events topic
```bash
docker exec kafka-broker-1 kafka-topics --bootstrap-server kafka-1:29092 --describe --topic streamsocial_events
```

### List consumer groups
```bash
docker exec kafka-broker-1 kafka-consumer-groups --bootstrap-server kafka-1:29092 --list
```

### Describe consumer group
```bash
docker exec kafka-broker-1 kafka-consumer-groups --bootstrap-server kafka-1:29092 --group streamsocial_event_consumers --describe
```

### View messages in topic (real-time)
```bash
docker exec kafka-broker-1 kafka-console-consumer --bootstrap-server kafka-1:29092 --topic streamsocial_events --from-beginning
```

---

## Event Types Supported

- `user_registration` - User registers for the platform
- `user_login` - User logs in
- `user_profile_update` - User updates profile
- `user_follow` - User follows another user
- `user_post_create` - User creates a post
- `user_post_delete` - User deletes a post
- `content_like` - User likes content
- `content_comment` - User comments on content
- `content_share` - User shares content
- `system_notification` - System sends notification

---

## Monitoring & Troubleshooting

### Check Consumer Thread Status
The consumer runs in a daemon thread that starts automatically when the FastAPI server starts.

### View Logs
The consumer logs all processed events with timestamps and any errors:
```
2026-07-25 15:30:45,123 - INFO - Consumer initialized with group: streamsocial_event_consumers
2026-07-25 15:30:45,456 - INFO - Starting event consumer...
2026-07-25 15:30:46,789 - INFO - Received event: <id> of type: user_registration
2026-07-25 15:30:46,890 - INFO - Event <id> processed by handler
```

### Consumer Not Receiving Events
1. Verify Kafka is running: `docker ps | grep kafka`
2. Verify topic exists: `docker exec kafka-broker-1 kafka-topics --bootstrap-server kafka-1:29092 --list`
3. Check bootstrap server addresses are correct
4. Check API: `GET http://localhost:8000/consumer/stats`

### Consumer Group Not Visible
Consumer groups are only created when a consumer connects. If you don't see the group:
1. Ensure events have been sent to trigger consumer connection
2. Check consumer logs for errors
3. Verify consumer is running: `GET http://localhost:8000/consumer/stats`

---

## Adding Custom Event Handlers

Edit `consumers/consumer_runner.py` to add handlers:

```python
def handle_custom_event(event_data: Dict[str, Any]):
    """Handle custom events"""
    logger.info(f"Processing custom event: {event_data}")
    # Your custom logic here

# In start_consuming():
self.register_handler('custom_event_type', self.handle_custom_event)
```

---

## Performance Notes

- Consumer keeps last 1000 events in memory
- Events older than that are available in Kafka for 7 days (default)
- Each event processes in < 1ms
- Consumer group maintains offset automatically (auto_offset_reset='earliest')
- Multiple consumer instances can be run for scaling (same group_id)

---

## Next Steps

1. **Scale Consumers**: Run multiple consumer instances with same `group_id`
2. **Add Real Storage**: Replace in-memory storage with database
3. **Add Webhooks**: Trigger external services on specific events
4. **Add Alerting**: Alert on critical events in real-time
5. **Add Analytics**: Track and analyze event patterns

