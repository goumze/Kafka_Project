"""
Optional in-process consumer state (API_EMBED_CONSUMER only).

Compose-scaled workers are the supported scale path. This service only
tracks an embedded consumer injected from main.py for local dev.
HTTP start/stop of Kafka consumers is intentionally not offered for scale.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from consumers.event_consumer import StreamSocialEventConsumer

logger = logging.getLogger("streamsocial.embedded_consumer")


class EmbeddedConsumerService:
    """Tracks optional in-process consumer instances (not Compose workers)."""

    def __init__(self) -> None:
        self._consumers: Dict[str, StreamSocialEventConsumer] = {}
        self._threads: Dict[str, Optional[threading.Thread]] = {}
        self._running: Dict[str, bool] = {}
        self._primary_id: Optional[str] = None

    def set_state(
        self,
        consumer: Optional[StreamSocialEventConsumer],
        consumer_thread: Optional[threading.Thread],
        consumer_running: bool,
        instance_id: str = "primary",
    ) -> None:
        """Inject state from main.py embedded mode."""
        if consumer is None:
            self._consumers.pop(instance_id, None)
        else:
            self._consumers[instance_id] = consumer
        self._threads[instance_id] = consumer_thread
        self._running[instance_id] = consumer_running
        self._primary_id = instance_id
        logger.info(
            "embedded_consumer_state instance_id=%s running=%s",
            instance_id,
            consumer_running,
        )

    def get_state(
        self, instance_id: Optional[str] = None
    ) -> Tuple[
        Optional[StreamSocialEventConsumer],
        Optional[threading.Thread],
        bool,
    ]:
        iid = instance_id or self._primary_id or "primary"
        return (
            self._consumers.get(iid),
            self._threads.get(iid),
            self._running.get(iid, False),
        )

    def set_running(self, value: bool, instance_id: str = "primary") -> None:
        self._running[instance_id] = value

    def list_instances(self) -> List[Dict[str, Any]]:
        instances: List[Dict[str, Any]] = []
        for iid, consumer in self._consumers.items():
            stats = consumer.get_stats() if consumer is not None else {}
            instances.append(
                {
                    "instance_id": iid,
                    "running": self._running.get(iid, False),
                    "assigned_partitions": stats.get("assigned_partitions", 0),
                    "total_events": stats.get("total_events", 0),
                    "total_lag": stats.get("total_lag", 0),
                }
            )
        return instances

    def in_process_stats(self, instance_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        iid = instance_id or self._primary_id
        if not iid or iid not in self._consumers:
            return None
        consumer = self._consumers[iid]
        if consumer is None:
            return None
        stats = consumer.get_stats()
        return {
            "status": "running" if self._running.get(iid) else "stopped",
            "mode": "in_process",
            "instance_id": iid,
            "running": self._running.get(iid, False),
            **stats,
        }

    def stop_instance(self, instance_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop an embedded in-process consumer if present."""
        iid = instance_id or self._primary_id or "primary"
        if not self._running.get(iid) and iid not in self._consumers:
            return {
                "status": "already_stopped",
                "instance_id": iid,
                "message": f"Consumer instance {iid} is not running in-process",
            }
        try:
            self._running[iid] = False
            consumer = self._consumers.get(iid)
            if consumer is not None:
                consumer.stop()
                consumer.close()
            logger.info("embedded_consumer_stopped instance_id=%s", iid)
            return {
                "status": "stopped",
                "instance_id": iid,
                "message": f"Kafka consumer instance {iid} stopped successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.exception("Failed to stop embedded consumer %s", iid)
            return {
                "status": "error",
                "instance_id": iid,
                "message": f"Failed to stop consumer {iid}: {exc}",
            }

    def has_instances(self) -> bool:
        return bool(self._consumers)

    def active_count(self) -> int:
        return sum(1 for running in self._running.values() if running)

    def get_consumer(
        self, instance_id: Optional[str] = None
    ) -> Optional[StreamSocialEventConsumer]:
        iid = instance_id or self._primary_id or "primary"
        return self._consumers.get(iid)


# Process-wide singleton used by API controllers / main embed path
embedded_consumer_service = EmbeddedConsumerService()
