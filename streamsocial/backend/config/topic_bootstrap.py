"""
Topic creation / ensure helpers.

Used by API startup, producers, and consumer workers. Kept outside metrics
so lag computation does not own infrastructure bootstrap.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Set

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from config.settings import Settings, get_settings
from config.topic_config import StreamSocialTopicManager

logger = logging.getLogger("streamsocial.topic_bootstrap")


def planned_topic_specs(settings: Optional[Settings] = None) -> List[dict]:
    """
    Pure helper: return the topic specs that would be ensured.

    No Kafka I/O — safe for unit tests.
    """
    cfg = settings or get_settings()
    manager = StreamSocialTopicManager(settings=cfg)
    specs: List[dict] = []
    for topic_config in manager.get_all_topics().values():
        specs.append(
            {
                "name": topic_config.name,
                "num_partitions": topic_config.num_partitions,
                "replication_factor": topic_config.replication_factor,
                "compression_type": topic_config.compression_type,
                "retention_ms": topic_config.retention_ms,
            }
        )
    return specs


def topic_names(settings: Optional[Settings] = None) -> List[str]:
    """Configured topic names (no Kafka I/O)."""
    return [spec["name"] for spec in planned_topic_specs(settings)]


def ensure_topics_exist(settings: Optional[Settings] = None) -> Set[str]:
    """
    Create configured topics if missing.

    Returns the set of topic names that are known after the call
    (created or already present in config).
    """
    cfg = settings or get_settings()
    manager = StreamSocialTopicManager(settings=cfg)
    known = set(manager.get_all_topic_names())
    admin: Optional[KafkaAdminClient] = None
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=cfg.bootstrap_servers,
            client_id="streamsocial-topic-bootstrap",
            request_timeout_ms=15000,
        )
        existing = set(admin.list_topics())
        to_create: List[NewTopic] = []
        for topic_config in manager.get_all_topics().values():
            if topic_config.name in existing:
                continue
            to_create.append(
                NewTopic(
                    name=topic_config.name,
                    num_partitions=topic_config.num_partitions,
                    replication_factor=topic_config.replication_factor,
                    topic_configs={
                        "compression.type": topic_config.compression_type,
                        "retention.ms": str(topic_config.retention_ms),
                    },
                )
            )
        if to_create:
            try:
                admin.create_topics(to_create, validate_only=False)
                logger.info("Created topics: %s", [t.name for t in to_create])
            except TopicAlreadyExistsError:
                logger.info("Topics already exist during create race")
        else:
            logger.info("All configured topics already exist")
    finally:
        if admin is not None:
            try:
                admin.close()
            except Exception:
                logger.debug("admin close failed", exc_info=True)
    return known


def try_ensure_topics_exist(settings: Optional[Settings] = None) -> bool:
    """Best-effort topic bootstrap (does not raise)."""
    try:
        ensure_topics_exist(settings=settings)
        return True
    except Exception:
        logger.exception("try_ensure_topics_exist failed")
        return False
