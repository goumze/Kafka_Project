"""
Consumer Controller
Handles Kafka consumer management: starting, stopping, and status monitoring.
"""

import threading
from typing import Optional

from consumers.consumer_runner import StreamSocialEventConsumer
from fastapi import APIRouter

router = APIRouter(prefix="/consumer", tags=["consumer"])


_consumer: Optional[StreamSocialEventConsumer] = None
_consumer_thread: Optional[threading.Thread] = None
_consumer_running: bool = False


def set_consumer_state(consumer, consumer_thread, consumer_running):
    """Inject consumer state dependencies"""
    global _consumer, _consumer_thread, _consumer_running
    _consumer = consumer
    _consumer_thread = consumer_thread
    _consumer_running = consumer_running


def get_consumer_state():
    """Get current consumer state"""
    return _consumer, _consumer_thread, _consumer_running


def set_consumer_running(value: bool):
    """Update consumer running state"""
    global _consumer_running
    _consumer_running = value


def run_consumer_in_background():
    """Run the consumer in a background thread"""
    global _consumer, _consumer_running
    try:
        if _consumer is None:
            _consumer = StreamSocialEventConsumer()
        _consumer_running = True
        _consumer.start_consuming()
        print("Kafka consumer started in background thread.")
    except Exception as e:
        print(f"Error in consumer thread: {str(e)}")
        _consumer_running = False


@router.get("/stats")
async def get_consumer_stats():
    """Get Kafka consumer statistics and status"""
    if _consumer is None:
        return {
            "status": "not_initialized",
            "running": _consumer_running,
            "total_events_processed": 0,
            "events_in_memory": 0
        }
    
    stats = _consumer.get_stats()
    return {
        "status": "running" if _consumer_running else "stopped",
        "running": _consumer_running,
        **stats
    }


@router.post("/start")
async def start_consumer():
    """Start the Kafka consumer"""
    global _consumer, _consumer_thread, _consumer_running
    
    if _consumer_running:
        return {"status": "already_running", "message": "Consumer is already running"}
    
    try:
        if _consumer is None:
            _consumer = StreamSocialEventConsumer()
        
        _consumer_thread = threading.Thread(target=run_consumer_in_background, daemon=True)
        _consumer_thread.start()
        
        return {
            "status": "started",
            "message": "Kafka consumer started successfully",
            "running": _consumer_running
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start consumer: {str(e)}"
        }


@router.post("/stop")
async def stop_consumer():
    """Stop the Kafka consumer"""
    global _consumer, _consumer_running
    
    if not _consumer_running:
        return {"status": "already_stopped", "message": "Consumer is not running"}
    
    try:
        _consumer_running = False
        if _consumer:
            _consumer.consumer.close()
        return {
            "status": "stopped",
            "message": "Kafka consumer stopped successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop consumer: {str(e)}"
        }
