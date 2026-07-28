"""
Cluster Controller
Handles Kafka cluster management: health monitoring, partition leadership,
broker failure simulation, and consumer rebalancing.
"""

import subprocess
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/cluster", tags=["cluster"])

# Kafka cluster configuration
KAFKA_BROKERS = ['localhost:9092', 'localhost:9093', 'localhost:9094']
BROKER_CONTAINERS = ['kafka-broker-1', 'kafka-broker-2', 'kafka-broker-3']
TOPIC_NAME = 'streamsocial_events'


class BrokerFailureSimulation(BaseModel):
    broker_name: str


@router.get("/health")
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


@router.get("/metadata")
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


@router.get("/partitions")
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


@router.post("/simulate-failure")
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


@router.post("/recover-failure")
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


@router.get("/consumer-lag")
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


@router.post("/rebalance-consumers")
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
