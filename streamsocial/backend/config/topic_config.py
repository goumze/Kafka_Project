"""
Topic Configuration and Management System
Defines all Kafka topics with their partition strategies and configurations
for StreamSocial platform.
"""

from dataclasses import dataclass
from typing import List, Dict, Callable
from enum import Enum


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
    partition_key_extractor: Callable = None


class StreamSocialTopicManager:
    """
    Centralized topic configuration manager for StreamSocial.
    
    Defines topics with optimal partition counts based on:
    - Throughput requirements (50M req/s)
    - Single consumer capacity (~50K req/s)
    - Partition count formula: Target Throughput / Consumer Throughput
    - Safety buffer: 1.5x multiplier
    
    For StreamSocial:
    - user-actions: 1000 partitions (50M / 50K = 1000 minimum)
    - content-interactions: 500 partitions (optimized for analytics)
    - system-events: 100 partitions (lower volume)
    """
    
    # Topic Definitions with calculated partition counts
    TOPICS = {
        TopicType.USER_ACTIONS: TopicConfig(
            name="user-actions",
            num_partitions=1000,
            replication_factor=3,
            retention_ms=604800000,  # 7 days
            compression_type="gzip",
            description="User action events: posts, comments, follows, profile updates. "
                       "Partitioned by user_id for ordering guarantee.",
            partition_key_extractor=lambda event: event.get('user_id')
        ),
        TopicType.CONTENT_INTERACTIONS: TopicConfig(
            name="content-interactions",
            num_partitions=500,
            replication_factor=3,
            retention_ms=86400000,  # 1 day
            compression_type="gzip",
            description="Content interaction events: likes, shares, views, analytics. "
                       "Partitioned by content_id for analytics processing.",
            partition_key_extractor=lambda event: event.get('content_id')
        ),
        TopicType.SYSTEM_EVENTS: TopicConfig(
            name="system-events",
            num_partitions=100,
            replication_factor=3,
            retention_ms=259200000,  # 3 days
            compression_type="gzip",
            description="System events: notifications, errors, system alerts.",
            partition_key_extractor=lambda event: event.get('system_id', 'default')
        ),
    }
    
    # Event Type to Topic Mapping
    EVENT_TO_TOPIC_MAP = {
        # User Actions (1000 partitions)
        "user_registration": TopicType.USER_ACTIONS,
        "user_login": TopicType.USER_ACTIONS,
        "user_profile_update": TopicType.USER_ACTIONS,
        "user_follow": TopicType.USER_ACTIONS,
        "user_post_create": TopicType.USER_ACTIONS,
        "user_post_delete": TopicType.USER_ACTIONS,
        
        # Content Interactions (500 partitions)
        "content_like": TopicType.CONTENT_INTERACTIONS,
        "content_comment": TopicType.CONTENT_INTERACTIONS,
        "content_share": TopicType.CONTENT_INTERACTIONS,
        
        # System Events (100 partitions)
        "system_notification": TopicType.SYSTEM_EVENTS,
    }
    
    @classmethod
    def get_topic_config(cls, topic_type: TopicType) -> TopicConfig:
        """Get configuration for a specific topic type"""
        return cls.TOPICS.get(topic_type)
    
    @classmethod
    def get_all_topics(cls) -> Dict[TopicType, TopicConfig]:
        """Get all topic configurations"""
        return cls.TOPICS
    
    @classmethod
    def get_topic_for_event(cls, event_type: str) -> TopicType:
        """
        Determine which topic an event should be published to.
        
        Args:
            event_type: The event type string
            
        Returns:
            TopicType for the given event
        """
        event_type_normalized = event_type.lower()
        return cls.EVENT_TO_TOPIC_MAP.get(
            event_type_normalized, 
            TopicType.SYSTEM_EVENTS  # Default fallback
        )
    
    @classmethod
    def get_partition_key_extractor(cls, topic_type: TopicType) -> Callable:
        """
        Get the partition key extractor function for a topic.
        
        Args:
            topic_type: The topic type
            
        Returns:
            Callable that extracts partition key from event data
        """
        topic_config = cls.get_topic_config(topic_type)
        return topic_config.partition_key_extractor
    
    @classmethod
    def get_all_topic_names(cls) -> List[str]:
        """Get list of all topic names"""
        return [config.name for config in cls.TOPICS.values()]
