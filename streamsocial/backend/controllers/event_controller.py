"""
Event Controller
Handles user event operations: registration and event retrieval.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from models.events import EventType

router = APIRouter(prefix="/events", tags=["events"])


class UserRegistration(BaseModel):
    username: str
    email: str
    source: str = "web"


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
        "count": stats['total_events_processed'],
        "events_in_memory": stats['events_in_memory']
    }
