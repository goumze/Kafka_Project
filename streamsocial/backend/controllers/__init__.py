"""
Controllers package for StreamSocial Backend API.
"""

from .cluster_controller import router as cluster_router
from .consumer_controller import router as consumer_router
from .event_controller import router as event_router
from .health_controller import router as health_router
from .metrics_controller import router as metrics_router

# Re-export modules for dependency injection from main
from . import consumer_controller, event_controller, metrics_controller

__all__ = [
    "event_router",
    "consumer_router",
    "cluster_router",
    "health_router",
    "metrics_router",
    "event_controller",
    "consumer_controller",
    "metrics_controller",
]
