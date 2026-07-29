"""
StreamSocial Event Consumer
Consumes events from multiple Kafka topics with dynamic configuration.
Supports horizontal scaling, lag monitoring, and event handler pipeline.
"""

import json
import time
from kafka import KafkaConsumer, TopicPartition
from typing import Dict, Any, List, Callable, Optional, Set
from datetime import datetime
from collections import defaultdict

from config.topic_config import StreamSocialTopicManager


class StreamSocialEventConsumer:
    """
    Consumer for StreamSocial events from multiple topics.
    
    Subscribes to:
    - user-actions: User activity events (1000 partitions)
    - content-interactions: Content engagement events (500 partitions)
    - system-events: System notifications and alerts (100 partitions)
    
    Features:
    - Horizontal scaling support (multiple instances in same consumer group)
    - Per-partition consumer lag monitoring
    - Event handler pipeline
    - Comprehensive statistics tracking
    - Automatic offset management
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str] = None,
        group_id: str = 'streamsocial_event_consumers',
        instance_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        auto_offset_reset: str = 'earliest'
    ):
        """
        Initialize the event consumer.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            group_id: Consumer group ID for coordination (shared across instances)
            instance_id: Optional unique identifier for this consumer instance (for logging)
            topics: Specific topics to subscribe to. If None, subscribes to all configured topics.
            auto_offset_reset: Where to start consuming from ('earliest' or 'latest')
        """
        self.bootstrap_servers = bootstrap_servers or [
            'localhost:9092',
            'localhost:9093',
            'localhost:9094'
        ]
        self.group_id = group_id
        self.instance_id = instance_id or f"consumer_{id(self)}"
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
            auto_commit_interval_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            session_timeout_ms=30000,
            max_poll_records=500,
            max_poll_interval_ms=300000,  # 5 minutes
        )
        
        # Event handlers by event type
        self.event_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        
        # Statistics tracking
        self.processed_events: List[Dict[str, Any]] = []
        self.stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'events_by_topic': defaultdict(int),
            'events_by_partition': defaultdict(int),
            'errors': 0,
            'handler_errors': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'assigned_partitions': set(),
        }
        
        # Lag tracking (partition -> latest_offset, committed_offset)
        self.partition_offsets: Dict[TopicPartition, Dict[str, int]] = {}
        self.lag_history: List[Dict[str, Any]] = []
        
        print(f"[CONSUMER {self.instance_id}] Initialized with group_id={group_id}")
        print(f"[CONSUMER {self.instance_id}] Subscribed to topics: {', '.join(self.topics)}")

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
        print(f"[CONSUMER {self.instance_id}] [HANDLER] Registered handler for event type: {event_type}")

    def start_consuming(self, max_messages: Optional[int] = None) -> None:
        """
        Start consuming messages from subscribed topics.
        
        Processes:
        - Message deserialization and parsing
        - Event handler invocation
        - Statistics and lag tracking
        - Offset management and commits
        
        Args:
            max_messages: Maximum messages to consume (None = infinite)
        """
        message_count = 0
        self.stats['start_time'] = datetime.now()
        
        print(f"[CONSUMER {self.instance_id}] Starting message consumption...")
        
        try:
            for message in self.consumer:
                try:
                    # Track assigned partitions
                    tp = TopicPartition(message.topic, message.partition)
                    self.stats['assigned_partitions'].add(tp)
                    
                    # Parse message
                    event_data = message.value if message.value else {}
                    event_type = event_data.get('event_type', 'unknown')
                    topic_name = message.topic
                    partition = message.partition
                    offset = message.offset
                    
                    # Update statistics
                    self.stats['total_events'] += 1
                    self.stats['events_by_type'][event_type] += 1
                    self.stats['events_by_topic'][topic_name] += 1
                    self.stats['events_by_partition'][f"{topic_name}-{partition}"] += 1
                    
                    # Track processed events (keep last 1000 for dashboard)
                    if len(self.processed_events) >= 1000:
                        self.processed_events.pop(0)
                    
                    self.processed_events.append({
                        **event_data,
                        'processed_at': datetime.now().isoformat(),
                        'topic': topic_name,
                        'partition': partition,
                        'offset': offset
                    })
                    
                    # Log consumption
                    if self.stats['total_events'] % 1000 == 0:
                        print(f"[CONSUMER {self.instance_id}] [PROGRESS] {self.stats['total_events']:,} events processed")
                    
                    # Call registered handler if exists
                    if event_type in self.event_handlers:
                        try:
                            self.event_handlers[event_type](event_data)
                        except Exception as handler_error:
                            self.stats['handler_errors'] += 1
                            print(f"[CONSUMER {self.instance_id}] [HANDLER_ERROR] {event_type}: {handler_error}")
                    
                    message_count += 1
                    if max_messages and message_count >= max_messages:
                        break
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    print(f"[CONSUMER {self.instance_id}] [ERROR] Failed to process message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n[CONSUMER {self.instance_id}] Shutting down after {message_count} messages")
        finally:
            self.stats['end_time'] = datetime.now()
            self._print_stats()
            self.close()

    def _invoke_handler(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Invoke the registered handler for an event type.
        
        Args:
            event_type: Type of event
            event_data: Event payload
        """
        if event_type in self.event_handlers:
            try:
                handler = self.event_handlers[event_type]
                handler(event_data)
            except Exception as e:
                self.stats['handler_errors'] += 1
                print(f"[CONSUMER {self.instance_id}] [HANDLER_ERROR] {event_type}: {e}")

    def get_consumer_lag(self) -> Dict[str, Dict[str, int]]:
        """
        Get consumer lag per partition (committed offset vs high water mark).
        
        Lag = HighWaterMark - CommittedOffset
        
        Returns:
            Dictionary with lag information per topic/partition:
            {
                'topic_name': {
                    'partition_id': {
                        'committed_offset': int,
                        'high_water_mark': int,
                        'lag': int
                    }
                }
            }
        """
        lag_by_topic = defaultdict(dict)
        
        try:
            # Get assigned partitions
            assigned_partitions = self.consumer.assignment()
            
            if not assigned_partitions:
                return {}
            
            # Get committed offsets
            committed = self.consumer.committed()
            
            for tp in assigned_partitions:
                committed_offset = 0
                if tp in committed and committed[tp] is not None:
                    committed_offset = committed[tp].offset
                
                # Get high water mark
                high_water_mark = self.consumer.highwater(tp)
                
                # Calculate lag
                lag = high_water_mark - committed_offset if high_water_mark else 0
                
                lag_by_topic[tp.topic][tp.partition] = {
                    'committed_offset': committed_offset,
                    'high_water_mark': high_water_mark,
                    'lag': max(0, lag)  # Lag should never be negative
                }
                
                self.partition_offsets[tp] = {
                    'committed': committed_offset,
                    'high_water_mark': high_water_mark,
                    'lag': max(0, lag)
                }
            
            # Record lag history
            total_lag = sum(
                v['lag'] 
                for topic_lags in lag_by_topic.values() 
                for v in topic_lags.values()
            )
            self.lag_history.append({
                'timestamp': datetime.now().isoformat(),
                'total_lag': total_lag,
                'by_topic': dict(lag_by_topic)
            })
            
            # Keep only last 100 lag snapshots
            if len(self.lag_history) > 100:
                self.lag_history.pop(0)
            
        except Exception as e:
            print(f"[CONSUMER {self.instance_id}] [ERROR] Failed to calculate lag: {e}")
        
        return dict(lag_by_topic)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive consumer statistics.
        
        Returns:
            Dictionary with:
            - total_events: Total events processed
            - events_by_type: Distribution by event type
            - events_by_topic: Distribution by topic
            - total_lag: Current total consumer lag
            - lag_by_topic: Per-topic lag breakdown
            - assigned_partitions: Number of partitions assigned
            - handler_errors: Number of handler failures
            - uptime_seconds: How long consumer has been running
        """
        end_time = self.stats['end_time'] or datetime.now()
        uptime = (end_time - self.stats['start_time']).total_seconds()
        
        lag_info = self.get_consumer_lag()
        total_lag = sum(
            v['lag'] 
            for topic_lags in lag_info.values() 
            for v in topic_lags.values()
        )
        
        return {
            'consumer_instance': self.instance_id,
            'group_id': self.group_id,
            'total_events': self.stats['total_events'],
            'uptime_seconds': uptime,
            'throughput_events_per_sec': self.stats['total_events'] / uptime if uptime > 0 else 0,
            'events_by_type': dict(self.stats['events_by_type']),
            'events_by_topic': dict(self.stats['events_by_topic']),
            'assigned_partitions': len(self.stats['assigned_partitions']),
            'total_lag': total_lag,
            'lag_by_topic': lag_info,
            'errors': self.stats['errors'],
            'handler_errors': self.stats['handler_errors'],
            'recent_events': self.get_processed_events(limit=10),
        }

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

    def _print_stats(self):
        """Print consumer statistics at shutdown"""
        stats = self.get_stats()
        print("\n" + "="*70)
        print(f"CONSUMER {self.instance_id} STATISTICS")
        print("="*70)
        print(f"Total Events Processed: {stats['total_events']:,}")
        print(f"Uptime: {stats['uptime_seconds']:.2f} seconds")
        print(f"Throughput: {stats['throughput_events_per_sec']:.0f} events/sec")
        print(f"Assigned Partitions: {stats['assigned_partitions']}")
        print(f"Total Consumer Lag: {stats['total_lag']:,}")
        print(f"Errors: {stats['errors']}")
        print(f"Handler Errors: {stats['handler_errors']}")
        print("\nEvents by Topic:")
        for topic, count in stats['events_by_topic'].items():
            print(f"  {topic:25} {count:10,}")
        print("="*70 + "\n")

    def close(self) -> None:
        """Close the consumer and release resources"""
        try:
            self.consumer.close()
            print(f"[CONSUMER {self.instance_id}] Closed consumer connection")
        except Exception as e:
            print(f"[CONSUMER {self.instance_id}] [ERROR] Error closing consumer: {e}") 

    