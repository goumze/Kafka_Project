"""
Health Controller
Handles health checks and API root endpoint information.
"""

from datetime import datetime
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "StreamSocial Backend",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "StreamSocial Event-Driven Backend",
        "version": "1.0.0",
        "kafka_integration": "enabled",
        "consumer_status": "running (check /consumer/stats)",
        "phase_6_enabled": True,
        "phase_7_enabled": True,
        "endpoints": {
            "health": "GET /health",
            "register_user": "POST /events/user/register",
            "get_events": "GET /events/recent",
            "consumer_stats": "GET /consumer/stats",
            "consumer_start": "POST /consumer/start",
            "consumer_stop": "POST /consumer/stop",
            "cluster_health": "GET /cluster/health",
            "cluster_metadata": "GET /cluster/metadata",
            "cluster_partitions": "GET /cluster/partitions",
            "consumer_lag": "GET /cluster/consumer-lag",
            "simulate_failure": "POST /cluster/simulate-failure",
            "recover_failure": "POST /cluster/recover-failure",
            "rebalance_consumers": "POST /cluster/rebalance-consumers"
        }
    }
