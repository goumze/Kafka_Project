"""
Consumer Controller
HTTP-only lag/status endpoints. Group lag via LagQueryService.
In-process consumer lifecycle is not started here (Compose workers preferred).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from config.settings import get_settings
from services.embedded_consumer_service import (
    EmbeddedConsumerService,
    embedded_consumer_service,
)
from services.lag_query_service import LagQueryService

logger = logging.getLogger("streamsocial.consumer_api")

router = APIRouter(prefix="/consumer", tags=["consumer"])

_embedded: EmbeddedConsumerService = embedded_consumer_service
_lag_service: Optional[LagQueryService] = None


def set_embedded_service(service: EmbeddedConsumerService) -> None:
    """Override embedded state tracker (tests / DI)."""
    global _embedded
    _embedded = service


def set_lag_query_service(service: LagQueryService) -> None:
    global _lag_service
    _lag_service = service


def set_consumer_state(
    consumer: Any,
    consumer_thread: Any,
    consumer_running: bool,
    instance_id: str = "primary",
) -> None:
    """Inject optional in-process consumer state (embedded mode only)."""
    _embedded.set_state(consumer, consumer_thread, consumer_running, instance_id)


def get_consumer_state(instance_id: Optional[str] = None) -> Any:
    return _embedded.get_state(instance_id)


def set_consumer_running(value: bool, instance_id: str = "primary") -> None:
    _embedded.set_running(value, instance_id)


def _lag() -> LagQueryService:
    global _lag_service
    if _lag_service is None:
        _lag_service = LagQueryService(settings=get_settings())
    return _lag_service


@router.get("/stats")
async def get_consumer_stats(
    instance_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Stats for an in-process consumer instance, plus group lag snapshot.
    When consumers are external, lag still comes from the group lag service.
    """
    settings = get_settings()
    group_lag = _lag().get_lag_dict()
    in_proc = _embedded.in_process_stats(instance_id)
    if in_proc is not None:
        return {**in_proc, "group_lag": group_lag}

    return {
        "status": "external_workers",
        "mode": "compose_scaled",
        "message": (
            "No in-process consumer. Workers should run as kafka-consumer service. "
            "Group lag is still available."
        ),
        "group_id": settings.consumer_group_id,
        "group_lag": group_lag,
        "total_lag": group_lag.get("total_lag", 0),
        "scale_hint": (
            "docker compose up -d --scale kafka-consumer=3"
        ),
    }


@router.get("/lag")
async def get_consumer_lag(
    instance_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Group-level consumer lag (preferred for the scale demo).

    Query param instance_id is accepted for backward compatibility; lag is
    always computed for the whole consumer group.
    """
    snapshot = _lag().get_lag_dict()
    snapshot["instance_id_filter"] = instance_id
    snapshot["source"] = "group_admin"
    return snapshot


@router.get("/instances")
async def list_consumer_instances() -> Dict[str, Any]:
    """List in-process instances only; Compose replicas are separate containers."""
    settings = get_settings()
    instances = _embedded.list_instances()
    group_lag = _lag().get_lag_dict()
    return {
        "total_in_process_instances": len(instances),
        "instances": instances,
        "group_id": settings.consumer_group_id,
        "group_lag": group_lag,
        "note": "Compose kafka-consumer replicas are not listed here; use group lag.",
    }


@router.post("/start")
async def start_consumer(
    instance_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    In-process consumer start is disabled for the scale path.

    Use Compose: docker compose ... up -d --scale kafka-consumer=N
    or set API_EMBED_CONSUMER=true (main embeds one worker at startup).
    """
    settings = get_settings()
    iid = instance_id or "primary"
    logger.info(
        "consumer_start_rejected instance_id=%s reason=compose_workers_only",
        iid,
    )
    return {
        "status": "disabled",
        "instance_id": iid,
        "message": (
            "HTTP start of in-process consumers is disabled. "
            "Scale with: docker compose up -d --scale kafka-consumer=N. "
            "For single-process local dev set API_EMBED_CONSUMER=true."
        ),
        "api_embed_consumer": settings.api_embed_consumer,
        "group_id": settings.consumer_group_id,
    }


@router.post("/stop")
async def stop_consumer(
    instance_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Stop an embedded in-process consumer if main.py started one."""
    result = _embedded.stop_instance(instance_id)
    if result.get("status") == "error":
        logger.error("consumer_stop_failed result=%s", result)
    return result


@router.get("/health")
async def consumer_health() -> Dict[str, Any]:
    settings = get_settings()
    group_lag = _lag().get_lag_dict()
    if _embedded.has_instances():
        healthy_count = _embedded.active_count()
        return {
            "status": "healthy" if healthy_count > 0 else "degraded",
            "mode": "in_process",
            "active_instances": healthy_count,
            "total_instances": len(_embedded.list_instances()),
            "group_lag": group_lag,
        }
    status = "healthy" if not group_lag.get("error") else "degraded"
    return {
        "status": status,
        "mode": "compose_scaled",
        "group_id": settings.consumer_group_id,
        "group_lag": group_lag,
        "message": "Consumers expected as separate kafka-consumer containers",
    }
