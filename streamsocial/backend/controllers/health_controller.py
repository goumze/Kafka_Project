"""
Health Controller
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "StreamSocial Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/")
async def root() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "service": "StreamSocial Event-Driven Backend",
        "version": "2.0.0",
        "kafka_integration": "enabled",
        "consumer_mode": (
            "embedded" if settings.api_embed_consumer else "compose_workers"
        ),
        "consumer_group_id": settings.consumer_group_id,
        "demo": {
            "narrative": "produce load -> observe lag -> scale consumers -> lag drains",
            "scale": (
                "docker compose -f docker-compose.yml -f docker-compose.backend.yml "
                "up -d --scale kafka-consumer=N"
            ),
        },
        "endpoints": {
            "health": "GET /health",
            "metrics": "GET /metrics",
            "metrics_lag": "GET /metrics/lag",
            "register_user": "POST /events/user/register",
            "bulk_generate": "POST /events/bulk/generate",
            "get_events": "GET /events/recent",
            "consumer_stats": "GET /consumer/stats",
            "consumer_lag": "GET /consumer/lag",
            "consumer_start": "POST /consumer/start (disabled; use Compose scale)",
            "consumer_stop": "POST /consumer/stop (embedded only)",
            "cluster_health": "GET /cluster/health",
            "cluster_metadata": "GET /cluster/metadata",
        },
    }
