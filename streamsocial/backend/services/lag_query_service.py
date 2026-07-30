"""
Lag query facade for HTTP controllers.

Wraps metrics.lag_service.ConsumerLagService so controllers never construct
Kafka admin/consumer clients directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.settings import Settings, get_settings
from metrics.lag_service import ConsumerLagService, LagSnapshot


class LagQueryService:
    """Application service for group-level consumer lag."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        lag_service: Optional[ConsumerLagService] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._lag_service = lag_service or ConsumerLagService(settings=self.settings)

    def get_snapshot(self, topics: Optional[List[str]] = None) -> LagSnapshot:
        return self._lag_service.get_lag(topics=topics)

    def get_lag_dict(self, topics: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.get_snapshot(topics=topics).to_dict()

    def metrics_payload(self) -> Dict[str, Any]:
        """Full /metrics body used by the scale demo."""
        from datetime import datetime, timezone

        lag = self.get_snapshot()
        payload = lag.to_dict()
        payload.update(
            {
                "service": "streamsocial-api",
                "consumer_group_id": self.settings.consumer_group_id,
                "bootstrap_servers": self.settings.bootstrap_servers,
                "partitions": {
                    "user-actions": self.settings.partitions_user_actions,
                    "content-interactions": self.settings.partitions_content_interactions,
                    "system-events": self.settings.partitions_system_events,
                },
                "demo": {
                    "consumer_processing_delay_ms_default": (
                        self.settings.consumer_processing_delay_ms
                    ),
                    "scale_hint": (
                        "docker compose -f docker-compose.yml "
                        "-f docker-compose.backend.yml up -d --scale kafka-consumer=N"
                    ),
                },
                "observed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return payload
