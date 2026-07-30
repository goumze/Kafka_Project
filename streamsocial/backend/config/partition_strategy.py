"""
Partition Strategy Engine for StreamSocial
Hash-based consistent partitioning for even message distribution and per-key order.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from config.settings import Settings, get_settings
from config.topic_config import StreamSocialTopicManager, TopicType


class PartitionStrategy:
    """
    Implements partition key calculation for different topic types.
    Uses hash-based distribution for consistent and even message placement.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[List[str]] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.bootstrap_servers = bootstrap_servers or self.settings.bootstrap_servers
        self.topic_manager = StreamSocialTopicManager(settings=self.settings)

    def calculate_partition(
        self,
        event_data: Dict[str, Any],
        topic_type: TopicType,
    ) -> int:
        topic_config = self.topic_manager.get_topic_config(topic_type)
        partition_key_extractor = topic_config.partition_key_extractor
        if not partition_key_extractor:
            raise ValueError(f"No partition key extractor for topic: {topic_type}")

        partition_key = partition_key_extractor(event_data)
        if not partition_key:
            raise ValueError(f"Could not extract partition key from event: {event_data}")

        return self._hash_to_partition(str(partition_key), topic_config.num_partitions)

    def calculate_partition_by_key(self, partition_key: str, num_partitions: int) -> int:
        return self._hash_to_partition(partition_key, num_partitions)

    @staticmethod
    def _hash_to_partition(key: str, num_partitions: int) -> int:
        hash_value = hashlib.sha256(f"{key}".encode()).hexdigest()
        return int(hash_value, 16) % num_partitions

    def get_partition_for_user_action(self, user_id: str) -> int:
        topic_config = self.topic_manager.get_topic_config(TopicType.USER_ACTIONS)
        return self._hash_to_partition(f"user_{user_id}", topic_config.num_partitions)

    def get_partition_for_content_interaction(self, content_id: str) -> int:
        topic_config = self.topic_manager.get_topic_config(TopicType.CONTENT_INTERACTIONS)
        return self._hash_to_partition(
            f"content_{content_id}", topic_config.num_partitions
        )

    def get_partition_for_system_event(self, system_id: str = "default") -> int:
        topic_config = self.topic_manager.get_topic_config(TopicType.SYSTEM_EVENTS)
        return self._hash_to_partition(f"system_{system_id}", topic_config.num_partitions)


class Strategy(PartitionStrategy):
    """Backward compatibility wrapper for Strategy class"""

    pass
