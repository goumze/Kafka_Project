"""
Event Controller
HTTP validation/response only; publishing and loadgen live in services.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from models.events import EventType
from producers.event_producer import StreamSocialEventProducer
from services.lag_query_service import LagQueryService
from services.load_generation_service import LoadGenerationService, LoadGenRequest

logger = logging.getLogger("streamsocial.event_api")

router = APIRouter(prefix="/events", tags=["events"])

_producer: Optional[StreamSocialEventProducer] = None
_consumer: Optional[Any] = None
_loadgen: LoadGenerationService = LoadGenerationService()
_lag: Optional[LagQueryService] = None


class UserRegistration(BaseModel):
    username: str
    email: str
    source: str = "web"


class BulkGenerationRequest(LoadGenRequest):
    """Request body for bulk event generation (alias of service model)."""

    pass


def set_producer(producer: Optional[StreamSocialEventProducer]) -> None:
    global _producer
    _producer = producer


def set_consumer(consumer: Optional[Any]) -> None:
    global _consumer
    _consumer = consumer


def set_load_generation_service(service: LoadGenerationService) -> None:
    global _loadgen
    _loadgen = service


def set_lag_query_service(service: LagQueryService) -> None:
    global _lag
    _lag = service


def _lag_service() -> LagQueryService:
    global _lag
    if _lag is None:
        _lag = LagQueryService()
    return _lag


@router.post("/user/register")
async def register_user(registration: UserRegistration) -> Dict[str, Any]:
    """Register a user and publish the event to Kafka"""
    user_id = str(uuid.uuid4())
    if _producer is None:
        logger.error("register_user failed: producer not configured")
        return {
            "success": False,
            "user_id": user_id,
            "error": "Producer not configured",
        }
    try:
        _producer.publish_event(
            event_type=EventType.USER_REGISTRATION,
            user_id=user_id,
            data={
                "username": registration.username,
                "email": registration.email,
                "source": registration.source,
            },
            flush=True,
        )
        return {
            "success": True,
            "user_id": user_id,
            "message": "User registration event published to Kafka",
        }
    except Exception as exc:
        logger.exception("Failed to publish user registration user_id=%s", user_id)
        return {"success": False, "user_id": user_id, "error": str(exc)}


@router.post("/bulk/generate")
async def bulk_generate_events(request: BulkGenerationRequest) -> Dict[str, Any]:
    """
    Generate bulk events for load testing and consumer lag demonstration.
    Prefer background=true so lag can be observed while production continues.
    """
    return _loadgen.generate(request)


@router.get("/bulk/status")
async def bulk_generate_status() -> Dict[str, Any]:
    return _loadgen.status()


@router.get("/recent")
async def get_recent_events() -> Dict[str, Any]:
    """Recent events from in-process consumer (if any) plus group lag."""
    group_lag = _lag_service().get_lag_dict()
    if _consumer is None:
        return {
            "success": True,
            "events": [],
            "count": 0,
            "message": (
                "No in-process consumer. Events are consumed by kafka-consumer workers. "
                "Use /metrics or /consumer/lag for group lag."
            ),
            "total_lag": group_lag.get("total_lag", 0),
            "group_lag": group_lag,
        }

    stats = _consumer.get_stats()
    return {
        "success": True,
        "events": stats["recent_events"],
        "count": stats["total_events"],
        "events_in_memory": len(stats["recent_events"]),
        "total_lag": stats.get("total_lag", 0),
        "group_lag": group_lag,
    }
