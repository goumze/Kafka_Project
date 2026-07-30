"""
StreamSocial Event Producer
High-throughput publisher with tunable batching and partition-key routing.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from kafka import KafkaProducer

from config.partition_strategy import PartitionStrategy
from config.settings import Settings, get_settings
from config.topic_bootstrap import ensure_topics_exist, try_ensure_topics_exist
from config.topic_config import StreamSocialTopicManager, TopicType
from models.events import EventType, StreamSocialEvent

logger = logging.getLogger("streamsocial.producer")


class StreamSocialEventProducer:
    """
    High-performance event producer for StreamSocial.

    Kafka client is created lazily so API import/startup does not block
    when brokers are still coming up.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[List[str]] = None,
        settings: Optional[Settings] = None,
        ensure_topics: bool = True,
    ):
        self.settings = settings or get_settings()
        self.bootstrap_servers = bootstrap_servers or self.settings.bootstrap_servers
        self.topic_manager = StreamSocialTopicManager(settings=self.settings)
        self.partition_strategy = PartitionStrategy(
            bootstrap_servers=self.bootstrap_servers,
            settings=self.settings,
        )
        self.created_topics = set()
        self._published = 0
        self._producer: Optional[KafkaProducer] = None
        self._ensure_topics_on_first_use = ensure_topics
        self._topics_ready = False

    @property
    def producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = self._build_producer()
            if self._ensure_topics_on_first_use and not self._topics_ready:
                self.try_ensure_topics_exist()
        return self._producer

    def _build_producer(self) -> KafkaProducer:
        acks: Any = self.settings.producer_acks
        if isinstance(acks, str) and acks.isdigit():
            acks = int(acks)

        base_kwargs = {
            "bootstrap_servers": self.bootstrap_servers,
            "acks": acks,
            "retries": self.settings.producer_retries,
            "compression_type": self.settings.producer_compression,
            "batch_size": self.settings.producer_batch_size,
            "linger_ms": self.settings.producer_linger_ms,
            "request_timeout_ms": 30000,
            "api_version_auto_timeout_ms": 3000,
            "key_serializer": lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            # Bytes pass-through; callers encode JSON to bytes before send.
            "value_serializer": lambda v: v if isinstance(v, (bytes, bytearray)) else (
                v.encode("utf-8") if isinstance(v, str) else v
            ),
        }
        defaults = getattr(KafkaProducer, "DEFAULT_CONFIG", {}) or {}
        if defaults:
            kwargs = {k: v for k, v in base_kwargs.items() if k in defaults or k.endswith("serializer")}
            for optional_key, optional_val in (
                ("buffer_memory", self.settings.producer_buffer_memory),
                ("max_in_flight_requests_per_connection", self.settings.producer_max_in_flight),
            ):
                if optional_key in defaults:
                    kwargs[optional_key] = optional_val
        else:
            kwargs = base_kwargs

        try:
            return KafkaProducer(**kwargs)
        except ValueError:
            logger.warning("Falling back to minimal KafkaProducer config")
            return KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                acks=acks,
                retries=self.settings.producer_retries,
                compression_type=self.settings.producer_compression,
                batch_size=self.settings.producer_batch_size,
                linger_ms=self.settings.producer_linger_ms,
                key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            )

    def ensure_topics_exist(self) -> None:
        """Create configured topics if they do not already exist."""
        ensure_topics_exist(settings=self.settings)
        self.created_topics.update(self.topic_manager.get_all_topic_names())
        self._topics_ready = True

    def try_ensure_topics_exist(self) -> bool:
        """Best-effort topic bootstrap (does not raise)."""
        ok = try_ensure_topics_exist(settings=self.settings)
        if ok:
            self.created_topics.update(self.topic_manager.get_all_topic_names())
            self._topics_ready = True
        return ok

    def publish_event(
        self,
        event_type: EventType,
        user_id: str,
        data: Dict[str, Any],
        content_id: Optional[str] = None,
        system_id: Optional[str] = None,
        flush: bool = False,
    ) -> None:
        """Publish an event to the appropriate topic with a stable partition key."""
        try:
            event = StreamSocialEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.now(),
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                data=data,
            )

            event_dict = event.model_dump(mode="json")
            if content_id:
                event_dict["content_id"] = content_id
            if system_id:
                event_dict["system_id"] = system_id

            topic_type = self.topic_manager.get_topic_for_event(event_type.value)
            topic_config = self.topic_manager.get_topic_config(topic_type)
            topic_name = topic_config.name

            if topic_type == TopicType.USER_ACTIONS:
                partition_key = f"user_{user_id}"
            elif topic_type == TopicType.CONTENT_INTERACTIONS:
                if not content_id:
                    raise ValueError(f"content_id required for {event_type}")
                partition_key = f"content_{content_id}"
            else:
                sid = system_id or data.get("system_id") or data.get("service") or "default"
                partition_key = f"system_{sid}"

            partition = self.partition_strategy.calculate_partition_by_key(
                partition_key,
                topic_config.num_partitions,
            )

            future = self.producer.send(
                topic=topic_name,
                value=json.dumps(event_dict).encode("utf-8"),
                key=partition_key,
                partition=partition,
            )
            if flush:
                future.get(timeout=10)

            self._published += 1
            every = max(1, self.settings.producer_log_every_n)
            if self._published % every == 0:
                logger.info(
                    "produced count=%s last_type=%s topic=%s partition=%s key=%s",
                    self._published,
                    event_type.value,
                    topic_name,
                    partition,
                    partition_key,
                )
        except Exception as exc:
            logger.error("Failed to publish event: %s", exc)
            raise

    def publish_user_action(
        self,
        event_type: EventType,
        user_id: str,
        data: Dict[str, Any],
    ) -> None:
        self.publish_event(event_type, user_id, data)

    def publish_content_interaction(
        self,
        event_type: EventType,
        user_id: str,
        content_id: str,
        data: Dict[str, Any],
    ) -> None:
        if not content_id:
            raise ValueError("content_id is required for content interactions")
        self.publish_event(event_type, user_id, data, content_id=content_id)

    def flush(self) -> None:
        if self._producer is not None:
            self._producer.flush()

    def close(self) -> None:
        if self._producer is None:
            return
        try:
            self._producer.flush()
        finally:
            self._producer.close()
            self._producer = None

    def get_topic_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        for topic_config in self.topic_manager.get_all_topics().values():
            info[topic_config.name] = {
                "partitions": topic_config.num_partitions,
                "replication_factor": topic_config.replication_factor,
                "retention_ms": topic_config.retention_ms,
                "compression": topic_config.compression_type,
                "description": topic_config.description,
                "created": topic_config.name in self.created_topics,
            }
        return info
