"""
Topic configuration for StreamSocial.

Partition counts default high enough for multi-replica consumers and are
overridable via Settings / environment for local demos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

from config.settings import Settings, get_settings


class TopicType(str, Enum):
    """Topic types in StreamSocial"""

    USER_ACTIONS = "user-actions"
    CONTENT_INTERACTIONS = "content-interactions"
    SYSTEM_EVENTS = "system-events"


@dataclass
class TopicConfig:
    """Configuration for a Kafka topic"""

    name: str
    num_partitions: int
    replication_factor: int = 3
    retention_ms: int = 604800000  # 7 days default
    compression_type: str = "gzip"
    description: str = ""
    partition_key_extractor: Optional[Callable] = None


class StreamSocialTopicManager:
    """
    Centralized topic configuration manager for StreamSocial.

    Partition counts come from Settings so demos can run with fewer
    partitions locally while still supporting horizontal consumer scale.
    """

    # Event Type to Topic Mapping
    EVENT_TO_TOPIC_MAP = {
        # User Actions
        "user_registration": TopicType.USER_ACTIONS,
        "user_login": TopicType.USER_ACTIONS,
        "user_logout": TopicType.USER_ACTIONS,
        "user_profile_update": TopicType.USER_ACTIONS,
        "user_follow": TopicType.USER_ACTIONS,
        "user_unfollow": TopicType.USER_ACTIONS,
        "user_post_create": TopicType.USER_ACTIONS,
        "user_post_delete": TopicType.USER_ACTIONS,
        "user_post_edit": TopicType.USER_ACTIONS,
        "user_comment_create": TopicType.USER_ACTIONS,
        "user_comment_delete": TopicType.USER_ACTIONS,
        # Content Interactions
        "content_like": TopicType.CONTENT_INTERACTIONS,
        "content_unlike": TopicType.CONTENT_INTERACTIONS,
        "content_comment": TopicType.CONTENT_INTERACTIONS,
        "content_share": TopicType.CONTENT_INTERACTIONS,
        "content_view": TopicType.CONTENT_INTERACTIONS,
        "content_bookmark": TopicType.CONTENT_INTERACTIONS,
        "content_analytics": TopicType.CONTENT_INTERACTIONS,
        # System Events
        "system_notification": TopicType.SYSTEM_EVENTS,
        "system_alert": TopicType.SYSTEM_EVENTS,
        "system_error": TopicType.SYSTEM_EVENTS,
        "system_health_check": TopicType.SYSTEM_EVENTS,
    }

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.TOPICS: Dict[TopicType, TopicConfig] = {
            TopicType.USER_ACTIONS: TopicConfig(
                name="user-actions",
                num_partitions=self.settings.partitions_user_actions,
                replication_factor=self.settings.replication_factor,
                retention_ms=604800000,
                compression_type="gzip",
                description=(
                    "User action events: posts, comments, follows, profile updates. "
                    "Partitioned by user_id for ordering guarantee."
                ),
                partition_key_extractor=lambda event: event.get("user_id"),
            ),
            TopicType.CONTENT_INTERACTIONS: TopicConfig(
                name="content-interactions",
                num_partitions=self.settings.partitions_content_interactions,
                replication_factor=self.settings.replication_factor,
                retention_ms=86400000,
                compression_type="gzip",
                description=(
                    "Content interaction events: likes, shares, views, analytics. "
                    "Partitioned by content_id for analytics processing."
                ),
                partition_key_extractor=lambda event: event.get("content_id"),
            ),
            TopicType.SYSTEM_EVENTS: TopicConfig(
                name="system-events",
                num_partitions=self.settings.partitions_system_events,
                replication_factor=self.settings.replication_factor,
                retention_ms=259200000,
                compression_type="gzip",
                description="System events: notifications, errors, system alerts.",
                partition_key_extractor=lambda event: event.get("system_id", "default"),
            ),
        }

    def get_topic_config(self, topic_type: TopicType) -> TopicConfig:
        """Get configuration for a specific topic type"""
        config = self.TOPICS.get(topic_type)
        if config is None:
            raise ValueError(f"Unknown topic type: {topic_type}")
        return config

    def get_all_topics(self) -> Dict[TopicType, TopicConfig]:
        """Get all topic configurations"""
        return self.TOPICS

    def get_topic_for_event(self, event_type: str) -> TopicType:
        """Determine which topic an event should be published to."""
        event_type_normalized = event_type.lower()
        return self.EVENT_TO_TOPIC_MAP.get(
            event_type_normalized,
            TopicType.SYSTEM_EVENTS,
        )

    def get_partition_key_extractor(self, topic_type: TopicType) -> Optional[Callable]:
        """Get the partition key extractor function for a topic."""
        return self.get_topic_config(topic_type).partition_key_extractor

    def get_all_topic_names(self) -> List[str]:
        """Get list of all topic names"""
        return [config.name for config in self.TOPICS.values()]
