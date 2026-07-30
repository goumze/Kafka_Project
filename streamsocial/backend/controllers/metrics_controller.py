"""
Metrics Controller
Group-level lag and demo metrics (works with external consumer workers).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter

from services.lag_query_service import LagQueryService

router = APIRouter(tags=["metrics"])

_lag: Optional[LagQueryService] = None


def set_lag_query_service(service: LagQueryService) -> None:
    global _lag
    _lag = service


def _service() -> LagQueryService:
    global _lag
    if _lag is None:
        _lag = LagQueryService()
    return _lag


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Prometheus-ish JSON metrics for the scale demo.

    Primary signal: consumer group total_lag and per-topic breakdown.
    """
    return _service().metrics_payload()


@router.get("/metrics/lag")
async def get_metrics_lag() -> Dict[str, Any]:
    """Alias focused on lag only."""
    return _service().get_lag_dict()
