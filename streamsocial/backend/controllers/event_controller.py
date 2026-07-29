"""
Event Controller
Handles event operations: registration, publishing, and bulk data generation.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

from models.events import EventType
from producers.data_generator import StreamSocialDataGenerator, GenerationConfig

router = APIRouter(prefix="/events", tags=["events"])


class UserRegistration(BaseModel):
    username: str
    email: str
    source: str = "web"


class BulkGenerationRequest(BaseModel):
    """Request body for bulk event generation"""
    events_per_second: int = 1000
    duration_seconds: int = 60
    num_unique_users: int = 10000
    num_unique_content: int = 50000


def set_producer(producer):
    """Inject producer dependency"""
    global _producer
    _producer = producer


def set_consumer(consumer):
    """Inject consumer dependency"""
    global _consumer
    _consumer = consumer


_producer: Optional[object] = None
_consumer: Optional[object] = None


@router.post("/user/register")
async def register_user(registration: UserRegistration):
    """Register a user and publish the event to Kafka"""
    user_id = str(uuid.uuid4())
    
    # Publish event to Kafka
    try:
        _producer.publish_event(
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


@router.post("/bulk/generate")
async def bulk_generate_events(request: BulkGenerationRequest):
    """
    Generate bulk events for load testing and consumer lag demonstration.
    
    This endpoint generates a high-volume stream of realistic events
    to test producer throughput and demonstrate consumer lag behavior.
    
    Parameters:
    - events_per_second: Target publishing rate (default: 1000)
    - duration_seconds: How long to generate events (default: 60)
    - num_unique_users: Number of unique user IDs (default: 10000)
    - num_unique_content: Number of unique content IDs (default: 50000)
    
    Example usage:
    POST /events/bulk/generate
    {
        "events_per_second": 5000,
        "duration_seconds": 120,
        "num_unique_users": 50000
    }
    """
    try:
        # Create configuration
        config = GenerationConfig(
            events_per_second=request.events_per_second,
            duration_seconds=request.duration_seconds,
            num_unique_users=request.num_unique_users,
            num_unique_content=request.num_unique_content,
        )
        
        # Generate events
        generator = StreamSocialDataGenerator()
        stats = generator.generate(config)
        generator.close()
        
        return {
            "success": True,
            "message": f"Generated {stats['total_events']:,} events",
            "statistics": {
                "total_events": stats['total_events'],
                "duration_seconds": stats['duration_seconds'],
                "average_throughput": stats['avg_throughput'],
                "errors": stats['errors'],
                "events_by_type": stats['events_by_type'],
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/recent")
async def get_recent_events():
    """Get recently consumed events"""
    if _consumer is None:
        return {
            "success": True,
            "events": [],
            "count": 0,
            "message": "Consumer not yet initialized"
        }
    
    stats = _consumer.get_stats()
    return {
        "success": True,
        "events": stats['recent_events'],
        "count": stats['total_events'],
        "events_in_memory": len(stats['recent_events']),
        "total_lag": stats.get('total_lag', 0),
    }
