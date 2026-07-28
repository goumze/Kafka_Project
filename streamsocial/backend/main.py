import uuid
import subprocess
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import threading
from typing import Optional, Dict, Any, List
from models.events import EventType

# Import consumer and producer
from consumers.consumer_runner import StreamSocialEventConsumer
from producers.event_producer import StreamSocialEventProducer

app = FastAPI(title="StreamSocial Backend API", version="1.0.0")

# Initialize producer
producer = StreamSocialEventProducer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global consumer instance
consumer: Optional[StreamSocialEventConsumer] = None
consumer_thread: Optional[threading.Thread] = None
consumer_running = False

# Kafka cluster configuration (Phase 6 & 7)
KAFKA_BROKERS = ['localhost:9092', 'localhost:9093', 'localhost:9094']
BROKER_CONTAINERS = ['kafka-broker-1', 'kafka-broker-2', 'kafka-broker-3']
TOPIC_NAME = 'streamsocial_events'

class UserRegistration(BaseModel):
    username: str
    email: str
    source: str = "web"

class BrokerFailureSimulation(BaseModel):
    broker_name: str

# Mock event for testing
def generate_mock_events():
    """Generate some mock events for demonstration"""
    mock_events = [
        {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "user_registration",
            "event_data": {"username": "alice", "email": "alice@example.com"},
            "timestamp": datetime.now().isoformat()
        },
        {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "content_like",
            "event_data": {"content_id": "post_123", "liked": True},
            "timestamp": datetime.now().isoformat()
        },
        {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "content_comment",
            "event_data": {"content_id": "post_456", "comment": "Great post!"},
            "timestamp": datetime.now().isoformat()
        },
    ]
    return mock_events

def run_consumer_in_background():
    """Run the consumer in a background thread"""
    global consumer, consumer_running
    try:
        if consumer is None:
            consumer = StreamSocialEventConsumer()
        consumer_running = True
        consumer.start_consuming()
        print("Kafka consumer started in background thread.")
    except Exception as e:
        print(f"Error in consumer thread: {str(e)}")
        consumer_running = False

@app.on_event("startup")
async def startup_event():
    """Start the Kafka consumer when the application starts"""
    global consumer_thread
    print("Starting Kafka consumer in background...")
    consumer_thread = threading.Thread(target=run_consumer_in_background, daemon=True)
    consumer_thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global consumer, consumer_running
    consumer_running = False
    if consumer:
        consumer.consumer.close()
    print("Kafka consumer stopped")

@app.post("/events/user/register")
async def register_user(registration: UserRegistration):
    """Register a user and publish the event to Kafka"""
    user_id = str(uuid.uuid4())
    
    # Publish event to Kafka
    try:
        producer.publish_event(
            event_type=EventType.USER_REGISTRATION,
            user_id=user_id,
            data={"username": registration.username, "email": registration.email}
        )
        return {
            "success": True,
            "user_id": user_id,
            "message": "User registration event published to Kafka"
        }
    except Exception as e:
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }

@app.get("/events/recent")
async def get_recent_events():
    """Get recently consumed events"""
    if consumer is None:
        return {
            "success": True,
            "events": [],
            "count": 0,
            "message": "Consumer not yet initialized"
        }
    
    stats = consumer.get_stats()
    return {
        "success": True,
        "events": stats['recent_events'],
        "count": stats['total_events_processed'],
        "events_in_memory": stats['events_in_memory']
    }

@app.get("/consumer/stats")
async def get_consumer_stats():
    """Get Kafka consumer statistics and status"""
    if consumer is None:
        return {
            "status": "not_initialized",
            "running": consumer_running,
            "total_events_processed": 0,
            "events_in_memory": 0
        }
    
    stats = consumer.get_stats()
    return {
        "status": "running" if consumer_running else "stopped",
        "running": consumer_running,
        **stats
    }

@app.post("/consumer/start")
async def start_consumer():
    """Start the Kafka consumer"""
    global consumer, consumer_thread, consumer_running
    
    if consumer_running:
        return {"status": "already_running", "message": "Consumer is already running"}
    
    try:
        if consumer is None:
            consumer = StreamSocialEventConsumer()
        
        consumer_thread = threading.Thread(target=run_consumer_in_background, daemon=True)
        consumer_thread.start()
        
        return {
            "status": "started",
            "message": "Kafka consumer started successfully",
            "running": consumer_running
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start consumer: {str(e)}"
        }

@app.post("/consumer/stop")
async def stop_consumer():
    """Stop the Kafka consumer"""
    global consumer, consumer_running
    
    if not consumer_running:
        return {"status": "already_stopped", "message": "Consumer is not running"}
    
    try:
        consumer_running = False
        if consumer:
            consumer.consumer.close()
        return {
            "status": "stopped",
            "message": "Kafka consumer stopped successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop consumer: {str(e)}"
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "StreamSocial Backend", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {
        "service": "StreamSocial Event-Driven Backend",
        "version": "1.0.0",
        "kafka_integration": "enabled",
        "consumer_status": "running" if consumer_running else "stopped",
        "phase_6_enabled": True,
        "phase_7_enabled": True,
        "endpoints": {
            "health": "GET /health",
            "register_user": "POST /events/user/register",
            "get_events": "GET /events/recent",
            "consumer_stats": "GET /consumer/stats",
            "consumer_start": "POST /consumer/start",
            "consumer_stop": "POST /consumer/stop",
            "cluster_health": "GET /cluster/health",
            "cluster_metadata": "GET /cluster/metadata",
            "cluster_partitions": "GET /cluster/partitions",
            "consumer_lag": "GET /cluster/consumer-lag",
            "simulate_failure": "POST /cluster/simulate-failure",
            "recover_failure": "POST /cluster/recover-failure",
            "rebalance_consumers": "POST /cluster/rebalance-consumers"
        }
    }

# ==================== PHASE 6 & 7: Cluster Management Endpoints ====================

@app.get("/cluster/health")
async def get_cluster_health():
    """
    Phase 6: Get overall cluster health status
    Returns broker status and partition health
    """
    try:
        result = subprocess.run(
            ["docker", "exec", "kafka-broker-1", "kafka-broker-api-versions", 
             "--bootstrap-server", "kafka-1:29092"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        broker_statuses = {}
        for i, container in enumerate(BROKER_CONTAINERS, 1):
            try:
                status_result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={container}", "--format", "{{.State}}"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                broker_statuses[container] = {
                    "status": status_result.stdout.strip(),
                    "broker_id": i
                }
            except:
                broker_statuses[container] = {"status": "unknown", "broker_id": i}
        
        healthy_brokers = sum(1 for b in broker_statuses.values() if b["status"] == "running")
        
        return {
            "status": "healthy" if healthy_brokers >= 2 else "degraded",
            "brokers": broker_statuses,
            "healthy_count": healthy_brokers,
            "total_brokers": len(BROKER_CONTAINERS),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/cluster/metadata")
async def get_cluster_metadata():
    """
    Phase 6: Get cluster topology and metadata
    Returns broker information and topic partition distribution
    """
    try:
        result = subprocess.run(
            ["docker", "exec", "kafka-broker-1", "kafka-topics", 
             "--bootstrap-server", "kafka-1:29092", "--describe",
             "--topic", TOPIC_NAME],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return {
            "topic": TOPIC_NAME,
            "brokers": BROKER_CONTAINERS,
            "bootstrap_servers": KAFKA_BROKERS,
            "replication_factor": 3,
            "partition_info": result.stdout if result.returncode == 0 else "Topic not found",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/cluster/partitions")
async def get_partition_leadership():
    """
    Phase 6: Monitor partition leadership distribution
    Shows which broker is leader for each partition
    """
    try:
        result = subprocess.run(
            ["docker", "exec", "kafka-broker-1", "kafka-topics",
             "--bootstrap-server", "kafka-1:29092", "--describe",
             "--topic", TOPIC_NAME],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        lines = result.stdout.strip().split('\n')
        partitions = {}
        
        for line in lines:
            if "Partition" in line and "Leader" in line:
                partitions[line] = True
        
        return {
            "topic": TOPIC_NAME,
            "partition_details": lines,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/cluster/simulate-failure")
async def simulate_broker_failure(request: BrokerFailureSimulation):
    """
    Phase 7: Simulate broker failure for fault tolerance testing
    Stops a broker and monitors cluster recovery
    """
    try:
        broker_name = request.broker_name
        
        if broker_name not in BROKER_CONTAINERS:
            raise HTTPException(status_code=400, detail=f"Unknown broker: {broker_name}")
        
        # Stop the broker
        stop_result = subprocess.run(
            ["docker", "stop", broker_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "status": "failure_simulated",
            "broker": broker_name,
            "action": "stopped",
            "message": f"Broker {broker_name} has been stopped. Cluster will rebalance.",
            "recovery_hint": f"Run: docker start {broker_name}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/cluster/recover-failure")
async def recover_broker_failure(request: BrokerFailureSimulation):
    """
    Phase 7: Recover a failed broker and trigger rebalancing
    """
    try:
        broker_name = request.broker_name
        
        if broker_name not in BROKER_CONTAINERS:
            raise HTTPException(status_code=400, detail=f"Unknown broker: {broker_name}")
        
        # Restart the broker
        restart_result = subprocess.run(
            ["docker", "start", broker_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "status": "recovery_initiated",
            "broker": broker_name,
            "action": "restarted",
            "message": f"Broker {broker_name} is restarting. Cluster will rebalance partitions.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/cluster/consumer-lag")
async def get_consumer_lag():
    """
    Phase 6 & 7: Monitor consumer lag across cluster
    Shows rebalancing and processing delays
    """
    try:
        result = subprocess.run(
            ["docker", "exec", "kafka-broker-1", "kafka-consumer-groups",
             "--bootstrap-server", "kafka-1:29092",
             "--group", "streamsocial_event_consumers",
             "--describe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        lines = result.stdout.strip().split('\n')
        
        return {
            "consumer_group": "streamsocial_event_consumers",
            "lag_info": lines,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/cluster/rebalance-consumers")
async def trigger_consumer_rebalance():
    """
    Phase 7: Trigger consumer group rebalancing
    Useful after broker failures to redistribute partitions
    """
    try:
        # Reset consumer group offset to trigger rebalance
        result = subprocess.run(
            ["docker", "exec", "kafka-broker-1", "kafka-consumer-groups",
             "--bootstrap-server", "kafka-1:29092",
             "--group", "streamsocial_event_consumers",
             "--reset-offsets", "--to-latest", "--execute"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "status": "rebalancing",
            "consumer_group": "streamsocial_event_consumers",
            "message": "Consumer group rebalancing initiated",
            "output": result.stdout if result.returncode == 0 else result.stderr,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
            

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



