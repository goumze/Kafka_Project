"""
StreamSocial Event Producer
Publishes events to appropriate Kafka topics based on event type.
Uses dynamic topic configuration and partition strategy for scalability.
"""

import json
import uuid
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.events import StreamSocialEvent, EventType
from config.topic_config import StreamSocialTopicManager, TopicType
from config.partition_strategy import PartitionStrategy


class StreamSocialEventProducer:
    """
    High-performance event producer for StreamSocial.
    
    Features:
    - Multiple topics with dynamic partition strategies
    - Automatic topic creation with optimal settings
    - Hash-based partition key calculation
    - Connection pooling and batching
    - Gzip compression for network efficiency
    """
    
    def __init__(self, bootstrap_servers: List[str] = None):
        """
        Initialize the event producer.
        
        Args:
            bootstrap_servers: List of Kafka broker addresses
                Default: ['localhost:9092', 'localhost:9093', 'localhost:9094']
        """
        self.bootstrap_servers = bootstrap_servers or [
            'localhost:9092',
            'localhost:9093',
            'localhost:9094'
        ]
        
        # Initialize producer with performance optimizations
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            acks='all',  # Wait for all replicas
            retries=10,
            compression_type='gzip',
            batch_size=16384,  # 16KB batch size
            linger_ms=10,  # Wait 10ms for batching
            request_timeout_ms=30000
        )
        
        # Initialize topic and partition management
        self.topic_manager = StreamSocialTopicManager()
        self.partition_strategy = PartitionStrategy(bootstrap_servers=self.bootstrap_servers)
        
        # Track created topics
        self.created_topics = set()
        
        # Ensure all configured topics exist on startup
        self.ensure_topics_exist()

    def ensure_topics_exist(self) -> None:
        """
        Create all configured topics if they don't already exist.
        
        Topics created:
        - user-actions: 1000 partitions, partitioned by user_id
        - content-interactions: 500 partitions, partitioned by content_id
        - system-events: 100 partitions, partitioned by system_id
        
        All topics:
        - Replication factor: 3
        - Compression: gzip
        - Retention: configured per topic type
        """
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=5000
            )
            
            # Get existing topics
            existing_topics = set(admin_client.list_topics().keys())
            
            # Build list of topics to create
            topics_to_create = []
            for topic_type, topic_config in self.topic_manager.get_all_topics().items():
                topic_name = topic_config.name
                
                if topic_name not in existing_topics:
                    new_topic = NewTopic(
                        name=topic_name,
                        num_partitions=topic_config.num_partitions,
                        replication_factor=topic_config.replication_factor,
                        topic_configs={
                            'compression.type': topic_config.compression_type,
                            'retention.ms': str(topic_config.retention_ms),
                        }
                    )
                    topics_to_create.append(new_topic)
                    print(f"[TOPIC] Preparing to create: {topic_name} "
                          f"({topic_config.num_partitions} partitions, "
                          f"replication={topic_config.replication_factor})")
            
            # Create topics in batch
            if topics_to_create:
                admin_client.create_topics(
                    new_topics=topics_to_create,
                    validate_only=False
                )
                print(f"[TOPIC] Successfully created {len(topics_to_create)} topics")
                for topic in topics_to_create:
                    self.created_topics.add(topic.name)
            else:
                print("[TOPIC] All configured topics already exist")
                self.created_topics.update(existing_topics)
            
            admin_client.close()
            
        except Exception as e:
            print(f"[ERROR] Failed to ensure topics exist: {e}")
            raise

    def publish_event(
        self,
        event_type: EventType,
        user_id: str,
        data: Dict[str, Any],
        content_id: Optional[str] = None
    ) -> None:
        """
        Publish an event to the appropriate topic.
        
        Event routing logic:
        - User actions (1000 partitions): Ordered by user_id
        - Content interactions (500 partitions): Ordered by content_id
        - System events (100 partitions): Ordered by system_id
        
        Args:
            event_type: Type of event (from EventType enum)
            user_id: User triggering the event
            data: Event payload
            content_id: Optional content ID for content interactions
        """
        try:
            # Create event object
            event = StreamSocialEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.now(),
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                data=data
            )
            
            # Serialize event to JSON
            event_dict = event.model_dump(mode='json')
            event_json_str = json.dumps(event_dict)
            event_bytes = event_json_str.encode('utf-8')
            
            # Determine target topic and partition key
            topic_type = self.topic_manager.get_topic_for_event(event_type.value)
            topic_config = self.topic_manager.get_topic_config(topic_type)
            topic_name = topic_config.name
            
            # Calculate partition key based on topic type
            if topic_type == TopicType.USER_ACTIONS:
                partition_key = f"user_{user_id}"
            elif topic_type == TopicType.CONTENT_INTERACTIONS:
                if not content_id:
                    raise ValueError(f"content_id required for {event_type}")
                partition_key = f"content_{content_id}"
            else:  # SYSTEM_EVENTS
                partition_key = event.get('system_id', 'default')
            
            # Calculate target partition
            partition = self.partition_strategy.calculate_partition_by_key(
                partition_key,
                topic_config.num_partitions
            )
            
            # Send to Kafka
            self.producer.send(
                topic=topic_name,
                value=event_bytes,
                key=partition_key.encode('utf-8'),
                partition=partition
            )
            
            # Log event publication
            print(f"[PRODUCED] {event_type.value:30} -> {topic_name:25} "
                  f"partition={partition:4} user_id={user_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to publish event: {e}")
            raise
    
    def publish_user_action(
        self,
        event_type: EventType,
        user_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Publish a user action event (posts, comments, follows, etc.).
        Routed to user-actions topic (1000 partitions).
        
        Args:
            event_type: User action event type
            user_id: User performing the action
            data: Action details
        """
        self.publish_event(event_type, user_id, data)
    
    def publish_content_interaction(
        self,
        event_type: EventType,
        user_id: str,
        content_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Publish a content interaction event (likes, shares, views, etc.).
        Routed to content-interactions topic (500 partitions).
        
        Args:
            event_type: Content interaction event type
            user_id: User performing the interaction
            content_id: Content being interacted with
            data: Interaction details
        """
        if not content_id:
            raise ValueError("content_id is required for content interactions")
        self.publish_event(event_type, user_id, data, content_id=content_id)
    
    def flush(self) -> None:
        """Flush all pending messages to Kafka"""
        self.producer.flush()
    
    def close(self) -> None:
        """Close the producer and release resources"""
        self.producer.close()
    
    def get_topic_info(self) -> Dict[str, Any]:
        """
        Get information about all configured topics.
        
        Returns:
            Dictionary with topic configurations
        """
        info = {}
        for topic_type, topic_config in self.topic_manager.get_all_topics().items():
            info[topic_config.name] = {
                'partitions': topic_config.num_partitions,
                'replication_factor': topic_config.replication_factor,
                'retention_ms': topic_config.retention_ms,
                'compression': topic_config.compression_type,
                'description': topic_config.description,
                'created': topic_config.name in self.created_topics
            }
        return info    



        