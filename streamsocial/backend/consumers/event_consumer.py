"""
StreamSocial Event Consumer
Consumes events from multiple Kafka topics with dynamic configuration.
"""

import json
from kafka import KafkaConsumer
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime

from config.topic_config import StreamSocialTopicManager


class StreamSocialEventConsumer:
    """
    Consumer for StreamSocial events from multiple topics.
    
    Subscribes to:
    - user-actions: User activity events
    - content-interactions: Content engagement events
    - system-events: System notifications and alerts
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str] = None,
        group_id: str = 'streamsocial_event_consumers',
        topics: Optional[List[str]] = None,
        auto_offset_reset: str = 'latest'
    ):
        """
        Initialize the event consumer.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            group_id: Consumer group ID for coordination
            topics: Specific topics to subscribe to. If None, subscribes to all configured topics.
            auto_offset_reset: Where to start consuming from ('latest' or 'earliest')
        """
        self.bootstrap_servers = bootstrap_servers or [
            'localhost:9092',
            'localhost:9093',
            'localhost:9094'
        ]
        self.group_id = group_id
        self.topic_manager = StreamSocialTopicManager()
        
        # Determine topics to subscribe to
        if topics is None:
            topics = self.topic_manager.get_all_topic_names()
        self.topics = topics
        
        # Initialize consumer
        self.consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            session_timeout_ms=30000,
            max_poll_records=500
        )
        
        # Event handlers by event type
        self.event_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.processed_events: List[Dict[str, Any]] = []
        
        print(f"[CONSUMER] Initialized with group_id={group_id}")
        print(f"[CONSUMER] Subscribed to topics: {', '.join(self.topics)}")

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a handler function for a specific event type.
        
        Args:
            event_type: Event type to handle
            handler: Callable that processes the event
        """
        self.event_handlers[event_type] = handler
        print(f"[HANDLER] Registered handler for event type: {event_type}")

    def start_consuming(self, max_messages: Optional[int] = None) -> None:
        """
        Start consuming messages from subscribed topics.
        
        Args:
            max_messages: Maximum messages to consume (None = infinite)
        """
        message_count = 0
        try:
            for message in self.consumer:
                try:
                    # Parse message
                    event_data = message.value if message.value else {}
                    event_type = event_data.get('event_type')
                    topic_name = message.topic
                    partition = message.partition
                    offset = message.offset
                    
                    # Track processing
                    self.processed_events.append({
                        **event_data,
                        'processed_at': datetime.now().isoformat(),
                        'topic': topic_name,
                        'partition': partition,
                        'offset': offset
                    })
                    
                    # Log consumption
                    print(f"[CONSUMED] {event_type:30} <- {topic_name:25} "
                          f"partition={partition:4} offset={offset}")
                    
                    # Call registered handler if exists
                    if event_type in self.event_handlers:
                        self.event_handlers[event_type](event_data)
                    
                    message_count += 1
                    if max_messages and message_count >= max_messages:
                        break
                        
                except Exception as e:
                    print(f"[ERROR] Failed to process message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n[CONSUMER] Shutting down after {message_count} messages")
        finally:
            self.close()

    def get_processed_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get processed events for monitoring/dashboard.
        
        Args:
            limit: Maximum number of recent events to return
            
        Returns:
            List of processed events
        """
        if limit:
            return self.processed_events[-limit:]
        return self.processed_events

    def get_consumer_lag(self) -> Dict[str, Dict[str, int]]:
        """
        Get consumer lag per partition.
        
        Returns:
            Dictionary with lag information per topic/partition
        """
        lag_info = {}
        for tp, offset_and_metadata in self.consumer.committed().items():
            current_offset = offset_and_metadata.offset if offset_and_metadata else 0
            lag_info.setdefault(tp.topic, {})[tp.partition] = current_offset
        return lag_info

    def close(self) -> None:
        """Close the consumer and release resources"""
        self.consumer.close()
        print("[CONSUMER] Closed consumer connection") 

    