"""
Cluster Controller
HTTP-only surface for demo cluster ops. Implementation in ClusterOpsService.
Requires CLUSTER_OPS_ENABLED=true and docker socket when using failure sim.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.cluster_ops_service import ClusterOpsService

logger = logging.getLogger("streamsocial.cluster_api")

router = APIRouter(prefix="/cluster", tags=["cluster"])

_ops: ClusterOpsService = ClusterOpsService()


def set_cluster_ops_service(service: ClusterOpsService) -> None:
    global _ops
    _ops = service


class BrokerFailureSimulation(BaseModel):
    broker_name: str = Field(..., min_length=1)


@router.get("/health")
async def get_cluster_health() -> Dict[str, Any]:
    """Overall cluster health (docker probe when ops enabled)."""
    return _ops.get_health()


@router.get("/metadata")
async def get_cluster_metadata() -> Dict[str, Any]:
    """Cluster topology and topic describe output."""
    return _ops.get_metadata()


@router.get("/partitions")
async def get_partition_leadership() -> Dict[str, Any]:
    """Partition leadership distribution for the demo topic."""
    return _ops.get_partition_leadership()


@router.post("/simulate-failure")
async def simulate_broker_failure(request: BrokerFailureSimulation) -> Dict[str, Any]:
    """Stop an allowlisted broker container (demo fault injection)."""
    result = _ops.simulate_failure(request.broker_name)
    if result.get("status") == "error":
        logger.error("simulate_failure failed: %s", result.get("message"))
    return result


@router.post("/recover-failure")
async def recover_broker_failure(request: BrokerFailureSimulation) -> Dict[str, Any]:
    """Restart an allowlisted broker container."""
    result = _ops.recover_failure(request.broker_name)
    if result.get("status") == "error":
        logger.error("recover_failure failed: %s", result.get("message"))
    return result


@router.get("/consumer-lag")
async def get_consumer_lag() -> Dict[str, Any]:
    """
    CLI-based lag describe.

    Prefer GET /metrics or GET /consumer/lag (no docker required).
    """
    return _ops.consumer_lag_cli()


@router.post("/rebalance-consumers")
async def trigger_consumer_rebalance() -> Dict[str, Any]:
    """Trigger consumer group offset reset / rebalance via docker CLI."""
    return _ops.trigger_rebalance()
