"""
Group-level consumer lag via Kafka admin + metadata probe.

Used by the API process so lag is visible even when consumers run in
separate Compose containers (not embedded in the API).

IMPORTANT: This probe must NOT join the worker consumer group. Joining
with the same group_id would trigger rebalances and steal partitions
from kafka-consumer replicas during GET /metrics polls.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from kafka import KafkaConsumer, TopicPartition
from kafka.admin import KafkaAdminClient

from config.settings import Settings, get_settings
from config.topic_config import StreamSocialTopicManager

logger = logging.getLogger("streamsocial.lag")


@dataclass
class LagSnapshot:
    """Point-in-time lag for a consumer group across configured topics."""

    group_id: str
    total_lag: int
    lag_by_topic: Dict[str, Dict[str, Any]]
    partition_count: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "group_id": self.group_id,
            "total_lag": self.total_lag,
            "lag_by_topic": self.lag_by_topic,
            "partition_count": self.partition_count,
            "timestamp": self.timestamp,
        }
        if self.error:
            payload["error"] = self.error
        return payload


def committed_offset_from_meta(meta: Any) -> int:
    """Normalize OffsetAndMetadata / int / None into a committed offset int."""
    if meta is None:
        return 0
    if hasattr(meta, "offset"):
        offset = int(meta.offset)
        return 0 if offset < 0 else offset
    try:
        offset = int(meta)
        return 0 if offset < 0 else offset
    except (TypeError, ValueError):
        return 0


def partition_lag(high_water_mark: int, committed_offset: int) -> int:
    """Lag = max(0, HWM - committed)."""
    return max(0, int(high_water_mark) - int(committed_offset))


def build_lag_by_topic(
    topic_partitions: Dict[str, List[int]],
    end_offsets: Dict[TopicPartition, int],
    committed: Dict[TopicPartition, Any],
) -> Tuple[Dict[str, Dict[str, Any]], int, int]:
    """
    Pure helper: assemble lag_by_topic structure.

    Returns (lag_by_topic, total_lag, partition_count).
    """
    lag_by_topic: Dict[str, Dict[str, Any]] = {}
    total_lag = 0
    partition_count = 0

    for topic, parts in topic_partitions.items():
        topic_lags: Dict[str, Any] = {}
        for p in parts:
            tp = TopicPartition(topic, p)
            end = int(end_offsets.get(tp, 0) or 0)
            committed_offset = committed_offset_from_meta(committed.get(tp))
            lag = partition_lag(end, committed_offset)
            topic_lags[str(p)] = {
                "committed_offset": committed_offset,
                "high_water_mark": end,
                "lag": lag,
            }
            total_lag += lag
            partition_count += 1
        lag_by_topic[topic] = topic_lags

    return lag_by_topic, total_lag, partition_count


def build_lag_probe_kwargs(
    bootstrap_servers: Any,
    client_id: str,
    *,
    consumer_timeout_ms: int = 1000,
    request_timeout_ms: int = 10000,
) -> Dict[str, Any]:
    """
    Build kwargs for a non-member lag metadata probe consumer.

    - Never sets group_id (must not join worker CONSUMER_GROUP).
    - Filters to KafkaConsumer.DEFAULT_CONFIG so kafka-python 3.x does not
      raise KafkaConfigurationError on removed keys such as
      api_version_auto_timeout_ms.
    """
    kwargs: Dict[str, Any] = {
        "bootstrap_servers": bootstrap_servers,
        "client_id": client_id,
        "enable_auto_commit": False,
        "consumer_timeout_ms": consumer_timeout_ms,
        "request_timeout_ms": request_timeout_ms,
    }
    defaults = getattr(KafkaConsumer, "DEFAULT_CONFIG", {}) or {}
    if defaults:
        kwargs = {k: v for k, v in kwargs.items() if k in defaults}
    kwargs.pop("group_id", None)
    return kwargs


class ConsumerLagService:
    """
    Computes consumer-group lag without joining the worker group.

    - High water marks: throwaway KafkaConsumer (no group_id)
    - Committed offsets: KafkaAdminClient.list_group_offsets for the worker group

    Lag per partition = max(0, high_water_mark - committed_offset)
    Missing commits are treated as offset 0 (earliest) for demo clarity.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.topic_manager = StreamSocialTopicManager(settings=self.settings)
        self.bootstrap_servers = self.settings.bootstrap_servers
        self.group_id = self.settings.consumer_group_id

    def get_lag(self, topics: Optional[List[str]] = None) -> LagSnapshot:
        topic_names = topics or self.topic_manager.get_all_topic_names()
        admin: Optional[KafkaAdminClient] = None
        probe: Optional[KafkaConsumer] = None

        try:
            client_suffix = uuid.uuid4().hex[:8]
            admin = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"streamsocial-lag-admin-{client_suffix}",
                request_timeout_ms=15000,
            )
            # Non-member probe: no group_id; configs filtered for kafka-python 3.x.
            probe = KafkaConsumer(
                **build_lag_probe_kwargs(
                    self.bootstrap_servers,
                    f"streamsocial-lag-probe-{client_suffix}",
                )
            )

            topic_partitions: Dict[str, List[int]] = {}
            all_tps: List[TopicPartition] = []
            for topic in topic_names:
                parts = probe.partitions_for_topic(topic)
                if not parts:
                    topic_partitions[topic] = []
                    continue
                sorted_parts = sorted(parts)
                topic_partitions[topic] = sorted_parts
                all_tps.extend(TopicPartition(topic, p) for p in sorted_parts)

            if not all_tps:
                return LagSnapshot(
                    group_id=self.group_id,
                    total_lag=0,
                    lag_by_topic={t: {} for t in topic_names},
                    partition_count=0,
                )

            end_offsets = probe.end_offsets(all_tps)
            committed_map = self._fetch_committed_offsets(admin, all_tps)

            lag_by_topic, total_lag, partition_count = build_lag_by_topic(
                topic_partitions,
                end_offsets,
                committed_map,
            )

            snapshot = LagSnapshot(
                group_id=self.group_id,
                total_lag=total_lag,
                lag_by_topic=lag_by_topic,
                partition_count=partition_count,
            )
            logger.info(
                "lag_snapshot group_id=%s total_lag=%s partitions=%s (non-member probe)",
                self.group_id,
                total_lag,
                partition_count,
            )
            return snapshot
        except Exception as exc:
            logger.exception("Failed to compute consumer lag: %s", exc)
            return LagSnapshot(
                group_id=self.group_id,
                total_lag=0,
                lag_by_topic={},
                partition_count=0,
                error=str(exc),
            )
        finally:
            if probe is not None:
                try:
                    probe.close()
                except Exception:
                    logger.debug("lag probe consumer close failed", exc_info=True)
            if admin is not None:
                try:
                    admin.close()
                except Exception:
                    logger.debug("lag admin close failed", exc_info=True)

    def _fetch_committed_offsets(
        self,
        admin: KafkaAdminClient,
        tps: List[TopicPartition],
    ) -> Dict[TopicPartition, Any]:
        """
        Fetch group committed offsets via admin API (does not join the group).

        Falls back to empty commits if the group is unknown / no offsets yet.
        """
        committed: Dict[TopicPartition, Any] = {tp: None for tp in tps}
        try:
            result = admin.list_group_offsets({self.group_id: tps})
            group_map = self._unwrap_group_offset_map(result)
            for tp, meta in group_map.items():
                committed[tp] = meta
            return committed
        except Exception as scoped_exc:
            logger.debug(
                "list_group_offsets(scoped) failed (%s); retry all offsets",
                scoped_exc,
            )

        try:
            result = admin.list_group_offsets({self.group_id: None})
            group_map = self._unwrap_group_offset_map(result)
            for tp, meta in group_map.items():
                if tp in committed:
                    committed[tp] = meta
            return committed
        except Exception as all_exc:
            logger.warning(
                "list_group_offsets failed group_id=%s err=%s (treating commits as 0)",
                self.group_id,
                all_exc,
            )
            return committed

    def _unwrap_group_offset_map(self, result: Any) -> Dict[TopicPartition, Any]:
        """
        Normalize admin.list_group_offsets return value to TP -> metadata.

        kafka-python may return:
          {group_id: {TopicPartition: OffsetAndMetadata}}
        or in some paths a flat TP map.
        """
        if not result:
            return {}
        if isinstance(result, dict) and self.group_id in result:
            inner = result.get(self.group_id) or {}
            if isinstance(inner, dict):
                return inner
            return {}
        if isinstance(result, dict):
            sample_key = next(iter(result), None)
            if isinstance(sample_key, TopicPartition):
                return result
        return {}
