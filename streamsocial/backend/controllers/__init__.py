"""
Controllers package for StreamSocial Backend API.
Organized by operational intent: events, consumer management, cluster management, and health.
"""

from .event_controller import router as event_router
from .consumer_controller import router as consumer_router
from .cluster_controller import router as cluster_router
from .health_controller import router as health_router

__all__ = [
    'event_router',
    'consumer_router',
    'cluster_router',
    'health_router',
]
