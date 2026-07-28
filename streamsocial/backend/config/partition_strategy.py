"""
Partition Strategy Engine for StreamSocial
Implements hash-based consistent partitioning for even message distribution.

Key Design Principles:
- Hash-based distribution ensures even load across partitions
- Consistent key mapping: same key always goes to same partition
- Separate strategies per topic type
- No timestamp-based keys (avoids hot partitions)
"""

import hashlib
from typing import Dict, Any, Optional
from config.topic_config import StreamSocialTopicManager, TopicType


class PartitionStrategy:
    """
    Implements partition key calculation for different topic types.
    Uses hash-based distribution for consistent and even message placement.
    """
    
    def __init__(self, bootstrap_servers: list = None):
        """
        Initialize partition strategy with topic configurations.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers (for future expansion)
        """
        self.bootstrap_servers = bootstrap_servers or ['localhost:9092']
        self.topic_manager = StreamSocialTopicManager()
    
    def calculate_partition(
        self, 
        event_data: Dict[str, Any], 
        topic_type: TopicType
    ) -> int:
        """
        Calculate target partition for an event based on topic type.
        
        Uses consistent hashing to ensure:
        1. Even distribution across partitions
        2. Same key always goes to same partition
        3. No hot partition creation
        
        Args:
            event_data: The event dictionary
            topic_type: The topic type (user-actions, content-interactions, etc.)
            
        Returns:
            Partition number (0 to num_partitions-1)
        """
        # Get topic configuration
        topic_config = self.topic_manager.get_topic_config(topic_type)
        if not topic_config:
            raise ValueError(f"Unknown topic type: {topic_type}")
        
        # Extract partition key using topic-specific extractor
        partition_key_extractor = topic_config.partition_key_extractor
        if not partition_key_extractor:
            raise ValueError(f"No partition key extractor for topic: {topic_type}")
        
        partition_key = partition_key_extractor(event_data)
        if not partition_key:
            raise ValueError(f"Could not extract partition key from event: {event_data}")
        
        # Calculate hash-based partition
        return self._hash_to_partition(
            partition_key, 
            topic_config.num_partitions
        )
    
    def calculate_partition_by_key(
        self,
        partition_key: str,
        num_partitions: int
    ) -> int:
        """
        Calculate partition for a given key and partition count.
        
        Args:
            partition_key: The key to partition on
            num_partitions: Total number of partitions
            
        Returns:
            Partition number (0 to num_partitions-1)
        """
        return self._hash_to_partition(partition_key, num_partitions)
    
    @staticmethod
    def _hash_to_partition(key: str, num_partitions: int) -> int:
        """
        Hash a key to a partition number using SHA-256.
        
        Hash-based approach ensures:
        - Uniform distribution across partitions
        - Consistent results for same key
        - No correlation with key values
        
        Args:
            key: The partition key
            num_partitions: Number of partitions
            
        Returns:
            Partition number (0 to num_partitions-1)
        """
        # Use SHA-256 for consistent hashing
        hash_value = hashlib.sha256(f"{key}".encode()).hexdigest()
        # Convert hex to integer and modulo by partition count
        return int(hash_value, 16) % num_partitions
    
    def get_partition_for_user_action(self, user_id: str) -> int:
        """
        Calculate partition for a user action event.
        User actions (1000 partitions) are partitioned by user_id
        to maintain ordering for a user's activities.
        
        Args:
            user_id: The user ID
            
        Returns:
            Partition number for user-actions topic (0-999)
        """
        topic_config = self.topic_manager.get_topic_config(TopicType.USER_ACTIONS)
        return self._hash_to_partition(f"user_{user_id}", topic_config.num_partitions)
    
    def get_partition_for_content_interaction(self, content_id: str) -> int:
        """
        Calculate partition for a content interaction event.
        Content interactions (500 partitions) are partitioned by content_id
        for efficient analytics processing.
        
        Args:
            content_id: The content ID
            
        Returns:
            Partition number for content-interactions topic (0-499)
        """
        topic_config = self.topic_manager.get_topic_config(TopicType.CONTENT_INTERACTIONS)
        return self._hash_to_partition(f"content_{content_id}", topic_config.num_partitions)
    
    def get_partition_for_system_event(self, system_id: str = "default") -> int:
        """
        Calculate partition for a system event.
        System events (100 partitions) are partitioned by system_id.
        
        Args:
            system_id: The system identifier (default: "default")
            
        Returns:
            Partition number for system-events topic (0-99)
        """
        topic_config = self.topic_manager.get_topic_config(TopicType.SYSTEM_EVENTS)
        return self._hash_to_partition(f"system_{system_id}", topic_config.num_partitions)


# Backward compatibility alias
class Strategy(PartitionStrategy):
    """Backward compatibility wrapper for Strategy class"""
    pass    

