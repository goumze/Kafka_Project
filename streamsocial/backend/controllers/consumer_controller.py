"""
Consumer Controller
Handles Kafka consumer management: starting, stopping, status monitoring, and lag tracking.
Supports multiple consumer instances for horizontal scaling.
"""

import threading
from typing import Optional, List, Dict, Any

from consumers.event_consumer import StreamSocialEventConsumer
from fastapi import APIRouter, Query

router = APIRouter(prefix="/consumer", tags=["consumer"])


# Support for multiple consumer instances (horizontal scaling)
_consumers: Dict[str, StreamSocialEventConsumer] = {}
_consumer_threads: Dict[str, threading.Thread] = {}
_consumer_running: Dict[str, bool] = {}
_primary_consumer_id: Optional[str] = None  # For backward compatibility


def set_consumer_state(consumer, consumer_thread, consumer_running, instance_id: str = "primary"):
    """
    Inject consumer state dependencies.
    
    Supports multiple consumer instances for horizontal scaling.
    """
    global _primary_consumer_id
    _consumers[instance_id] = consumer
    _consumer_threads[instance_id] = consumer_thread
    _consumer_running[instance_id] = consumer_running
    _primary_consumer_id = instance_id


def get_consumer_state(instance_id: Optional[str] = None):
    """Get current consumer state"""
    if instance_id is None:
        instance_id = _primary_consumer_id or "primary"
    
    return (
        _consumers.get(instance_id),
        _consumer_threads.get(instance_id),
        _consumer_running.get(instance_id, False)
    )


def set_consumer_running(value: bool, instance_id: str = "primary"):
    """Update consumer running state"""
    _consumer_running[instance_id] = value


def run_consumer_in_background(instance_id: str = "primary"):
    """Run the consumer in a background thread"""
    try:
        consumer = _consumers.get(instance_id)
        if consumer is None:
            consumer = StreamSocialEventConsumer(instance_id=instance_id)
            _consumers[instance_id] = consumer
        
        _consumer_running[instance_id] = True
        consumer.start_consuming()
        print(f"[CONSUMER {instance_id}] Started in background thread.")
    except Exception as e:
        print(f"[ERROR] Error in consumer thread {instance_id}: {str(e)}")
        _consumer_running[instance_id] = False


@router.get("/stats")
async def get_consumer_stats(instance_id: Optional[str] = Query(None)):
    """
    Get Kafka consumer statistics and status.
    
    Supports querying individual consumer instances in a consumer group.
    If no instance_id specified, returns stats for primary consumer.
    """
    if instance_id is None:
        instance_id = _primary_consumer_id or "primary"
    
    consumer = _consumers.get(instance_id)
    
    if consumer is None:
        return {
            "status": "not_initialized",
            "instance_id": instance_id,
            "running": _consumer_running.get(instance_id, False),
            "total_events": 0,
            "total_lag": 0,
        }
    
    stats = consumer.get_stats()
    return {
        "status": "running" if _consumer_running.get(instance_id) else "stopped",
        "instance_id": instance_id,
        "running": _consumer_running.get(instance_id, False),
        **stats
    }


@router.get("/lag")
async def get_consumer_lag(instance_id: Optional[str] = Query(None)):
    """
    Get detailed consumer lag metrics per partition.
    
    Returns:
    - Total lag across all partitions
    - Per-topic lag breakdown
    - Per-partition lag details
    
    Lag = HighWaterMark - CommittedOffset
    
    Example:
    GET /consumer/lag
    {
        "total_lag": 1500,
        "lag_by_topic": {
            "user-actions": {
                "0": {"committed_offset": 1000, "high_water_mark": 1500, "lag": 500},
                "1": {"committed_offset": 2000, "high_water_mark": 2500, "lag": 500}
            }
        }
    }
    """
    if instance_id is None:
        instance_id = _primary_consumer_id or "primary"
    
    consumer = _consumers.get(instance_id)
    
    if consumer is None:
        return {
            "status": "not_initialized",
            "instance_id": instance_id,
            "total_lag": 0,
            "lag_by_topic": {}
        }
    
    lag_info = consumer.get_consumer_lag()
    total_lag = sum(
        v['lag'] 
        for topic_lags in lag_info.values() 
        for v in topic_lags.values()
    )
    
    return {
        "instance_id": instance_id,
        "total_lag": total_lag,
        "lag_by_topic": lag_info,
        "timestamp": consumer.stats.get('start_time', '').isoformat() if consumer.stats.get('start_time') else None,
    }


@router.get("/instances")
async def list_consumer_instances():
    """
    List all active consumer instances in the consumer group.
    
    Returns:
    - List of consumer instance IDs
    - Status of each instance
    - Partition assignments for each instance
    """
    instances = []
    
    for instance_id, consumer in _consumers.items():
        stats = consumer.get_stats() if consumer else {}
        instances.append({
            "instance_id": instance_id,
            "running": _consumer_running.get(instance_id, False),
            "assigned_partitions": stats.get('assigned_partitions', 0),
            "total_events": stats.get('total_events', 0),
            "total_lag": stats.get('total_lag', 0),
        })
    
    return {
        "total_instances": len(instances),
        "instances": instances,
        "group_id": _consumers.get(list(_consumers.keys())[0]).group_id if _consumers else "unknown",
    }


@router.post("/start")
async def start_consumer(instance_id: Optional[str] = Query(None)):
    """
    Start a Kafka consumer instance.
    
    For horizontal scaling, specify different instance_ids to start
    multiple consumer instances in the same consumer group.
    """
    if instance_id is None:
        instance_id = _primary_consumer_id or "primary"
    
    if _consumer_running.get(instance_id):
        return {
            "status": "already_running",
            "instance_id": instance_id,
            "message": f"Consumer instance {instance_id} is already running"
        }
    
    try:
        if instance_id not in _consumers or _consumers[instance_id] is None:
            _consumers[instance_id] = StreamSocialEventConsumer(instance_id=instance_id)
        
        _consumer_threads[instance_id] = threading.Thread(
            target=run_consumer_in_background,
            args=(instance_id,),
            daemon=True
        )
        _consumer_threads[instance_id].start()
        
        return {
            "status": "started",
            "instance_id": instance_id,
            "message": f"Kafka consumer instance {instance_id} started successfully",
            "running": _consumer_running.get(instance_id, False)
        }
    except Exception as e:
        return {
            "status": "error",
            "instance_id": instance_id,
            "message": f"Failed to start consumer {instance_id}: {str(e)}"
        }


@router.post("/stop")
async def stop_consumer(instance_id: Optional[str] = Query(None)):
    """
    Stop a Kafka consumer instance.
    
    Gracefully shuts down the consumer and releases partitions
    for rebalancing to other instances in the consumer group.
    """
    if instance_id is None:
        instance_id = _primary_consumer_id or "primary"
    
    if not _consumer_running.get(instance_id):
        return {
            "status": "already_stopped",
            "instance_id": instance_id,
            "message": f"Consumer instance {instance_id} is not running"
        }
    
    try:
        _consumer_running[instance_id] = False
        consumer = _consumers.get(instance_id)
        if consumer:
            consumer.close()
        
        return {
            "status": "stopped",
            "instance_id": instance_id,
            "message": f"Kafka consumer instance {instance_id} stopped successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "instance_id": instance_id,
            "message": f"Failed to stop consumer {instance_id}: {str(e)}"
        }


@router.get("/health")
async def consumer_health():
    """Get health status of all consumer instances"""
    if not _consumers:
        return {"status": "unhealthy", "reason": "No consumers initialized"}
    
    healthy_count = sum(1 for running in _consumer_running.values() if running)
    total_count = len(_consumers)
    
    return {
        "status": "healthy" if healthy_count > 0 else "unhealthy",
        "active_instances": healthy_count,
        "total_instances": total_count,
        "instances": {
            instance_id: {
                "running": _consumer_running.get(instance_id, False),
                "lag": _consumers[instance_id].get_stats().get('total_lag', 0) if _consumers[instance_id] else 0
            }
            for instance_id in _consumers
        }
    }
