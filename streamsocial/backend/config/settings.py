"""
Central env-driven settings for StreamSocial Kafka scale demo.

All processes (API, consumer workers, loadgen) should read from here
so bootstrap servers, group id, and demo knobs stay aligned.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


def _split_csv(value: Optional[str], default: List[str]) -> List[str]:
    if not value or not value.strip():
        return list(default)
    return [part.strip() for part in value.split(",") if part.strip()]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_consumer_instance_id() -> str:
    """
    Unique-enough client/instance id for Compose replicas.

    Prefer explicit INSTANCE_ID, then HOSTNAME (Compose container id/name),
    then a random suffix so scaled replicas never share client_id.
    """
    explicit = os.getenv("INSTANCE_ID")
    if explicit and explicit.strip():
        return explicit.strip()
    hostname = os.getenv("HOSTNAME")
    if hostname and hostname.strip():
        return hostname.strip()
    return f"consumer-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for API, producers, and consumer workers."""

    kafka_brokers: List[str] = field(
        default_factory=lambda: ["localhost:9092", "localhost:9093", "localhost:9094"]
    )
    consumer_group_id: str = "streamsocial_event_consumers"
    consumer_instance_id: str = "consumer"
    api_embed_consumer: bool = False

    # Producer throughput knobs
    producer_acks: str = "all"
    producer_retries: int = 10
    producer_compression: str = "gzip"
    producer_batch_size: int = 32768
    producer_linger_ms: int = 50
    producer_buffer_memory: int = 67108864
    producer_max_in_flight: int = 5
    producer_log_every_n: int = 1000

    # Consumer demo knobs (processing delay induces lag under load)
    consumer_auto_offset_reset: str = "earliest"
    consumer_max_poll_records: int = 100
    consumer_max_poll_interval_ms: int = 300000
    consumer_session_timeout_ms: int = 30000
    consumer_processing_delay_ms: float = 2.0
    consumer_log_every_n: int = 500
    consumer_lag_log_interval_sec: float = 5.0

    # Load generator pacing
    loadgen_burst_size: int = 50

    # Topic partition counts (env-overridable; high enough for multi-replica scale)
    partitions_user_actions: int = 24
    partitions_content_interactions: int = 12
    partitions_system_events: int = 6
    replication_factor: int = 3

    # Docker-based cluster demo ops (need docker socket when enabled)
    cluster_ops_enabled: bool = False
    broker_container_names: List[str] = field(
        default_factory=lambda: [
            "kafka-broker-1",
            "kafka-broker-2",
            "kafka-broker-3",
        ]
    )
    primary_broker_container: str = "kafka-broker-1"
    cluster_internal_bootstrap: str = "kafka-1:29092"
    cluster_demo_topic: str = "user-actions"

    log_level: str = "INFO"

    @property
    def bootstrap_servers(self) -> List[str]:
        return list(self.kafka_brokers)

    @classmethod
    def from_env(cls) -> "Settings":
        default_brokers = ["localhost:9092", "localhost:9093", "localhost:9094"]
        default_broker_containers = [
            "kafka-broker-1",
            "kafka-broker-2",
            "kafka-broker-3",
        ]
        broker_containers = _split_csv(
            os.getenv("BROKER_CONTAINER_NAMES"),
            default_broker_containers,
        )
        primary = os.getenv("PRIMARY_BROKER_CONTAINER") or (
            broker_containers[0] if broker_containers else "kafka-broker-1"
        )
        return cls(
            kafka_brokers=_split_csv(
                os.getenv("KAFKA_BROKERS") or os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
                default_brokers,
            ),
            consumer_group_id=os.getenv(
                "CONSUMER_GROUP", "streamsocial_event_consumers"
            ),
            consumer_instance_id=_resolve_consumer_instance_id(),
            api_embed_consumer=_env_bool("API_EMBED_CONSUMER", False),
            producer_acks=os.getenv("PRODUCER_ACKS", "all"),
            producer_retries=_env_int("PRODUCER_RETRIES", 10),
            producer_compression=os.getenv("PRODUCER_COMPRESSION", "gzip"),
            producer_batch_size=_env_int("PRODUCER_BATCH_SIZE", 32768),
            producer_linger_ms=_env_int("PRODUCER_LINGER_MS", 50),
            producer_buffer_memory=_env_int("PRODUCER_BUFFER_MEMORY", 67108864),
            producer_max_in_flight=_env_int("PRODUCER_MAX_IN_FLIGHT", 5),
            producer_log_every_n=_env_int("PRODUCER_LOG_EVERY_N", 1000),
            consumer_auto_offset_reset=os.getenv(
                "CONSUMER_AUTO_OFFSET_RESET", "earliest"
            ),
            consumer_max_poll_records=_env_int("CONSUMER_MAX_POLL_RECORDS", 50),
            consumer_max_poll_interval_ms=_env_int(
                "CONSUMER_MAX_POLL_INTERVAL_MS", 300000
            ),
            consumer_session_timeout_ms=_env_int("CONSUMER_SESSION_TIMEOUT_MS", 30000),
            # Default small delay helps lag demos; Compose sets this explicitly.
            consumer_processing_delay_ms=_env_float("CONSUMER_PROCESSING_DELAY_MS", 2.0),
            consumer_log_every_n=_env_int("CONSUMER_LOG_EVERY_N", 500),
            consumer_lag_log_interval_sec=_env_float(
                "CONSUMER_LAG_LOG_INTERVAL_SEC", 5.0
            ),
            loadgen_burst_size=_env_int("LOADGEN_BURST_SIZE", 50),
            partitions_user_actions=_env_int("PARTITIONS_USER_ACTIONS", 24),
            partitions_content_interactions=_env_int(
                "PARTITIONS_CONTENT_INTERACTIONS", 12
            ),
            partitions_system_events=_env_int("PARTITIONS_SYSTEM_EVENTS", 6),
            replication_factor=_env_int("KAFKA_REPLICATION_FACTOR", 3),
            cluster_ops_enabled=_env_bool("CLUSTER_OPS_ENABLED", False),
            broker_container_names=broker_containers,
            primary_broker_container=primary,
            cluster_internal_bootstrap=os.getenv(
                "CLUSTER_INTERNAL_BOOTSTRAP", "kafka-1:29092"
            ),
            cluster_demo_topic=os.getenv("CLUSTER_DEMO_TOPIC", "user-actions"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


def get_settings() -> Settings:
    """Load settings from environment (fresh each call for testability)."""
    return Settings.from_env()
