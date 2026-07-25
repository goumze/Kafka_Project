import json
import uuid
import logging
import time
import hashlib
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from models.events import StreamSocialEvent, EventType

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_BOOTSTRAP_SERVERS = ['localhost:9091', 'localhost:9092', 'localhost:9093']
RETENTION_MS = 7 * 24 * 60 * 60 * 1000  # 7 days in milliseconds


class ClusterAwareProducerConfig:
    """Configuration for cluster-aware producer settings."""
    
    def __init__(
        self,
        bootstrap_servers: List[str] = None,
        topic: str = 'streamsocial_events',
        partitions: int = 3,
        replication_factor: int = 3,
        min_insync_replicas: int = 2,
        batch_size: int = 16384,
        linger_ms: int = 10,
        compression_type: str = 'snappy',
        acks: str = 'all',
        retries: int = 3,
        retry_backoff_ms: int = 100,
        request_timeout_ms: int = 30000,
        max_in_flight_requests: int = 5,
    ):
        # Maintain backward compatibility with original port configuration
        self.bootstrap_servers = bootstrap_servers or DEFAULT_BOOTSTRAP_SERVERS
        self.topic = topic
        self.partitions = partitions
        self.replication_factor = replication_factor
        self.min_insync_replicas = min_insync_replicas
        self.batch_size = batch_size
        self.linger_ms = linger_ms
        self.compression_type = compression_type
        self.acks = acks
        self.retries = retries
        self.retry_backoff_ms = retry_backoff_ms
        self.request_timeout_ms = request_timeout_ms
        self.max_in_flight_requests = max_in_flight_requests


class StreamSocialEventProducer:
    """
    Cluster-Aware Kafka Producer for StreamSocial events.
    
    Features:
    - Cluster metadata discovery and management
    - Intelligent partitioning based on user_id for ordering guarantees
    - Automatic topic creation with cluster-aware replication
    - Retry logic with exponential backoff
    - Compression for efficient network usage
    - Health monitoring and broker awareness
    - Context manager support for resource management
    - Metrics collection for monitoring
    """
    
    def __init__(self, config: Optional[ClusterAwareProducerConfig] = None):
        """
        Initialize the cluster-aware producer.
        
        Args:
            config: ClusterAwareProducerConfig instance for customization
        """
        self.config = config or ClusterAwareProducerConfig()
        self.topic = self.config.topic
        self._metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'send_latency_ms': [],
        }
        
        # Initialize producer with cluster-aware settings
        self.producer = self._initialize_producer()
        
        # Initialize admin client for cluster management
        self.admin_client = self._initialize_admin_client()
        
        # Ensure topic exists with proper configuration
        self._ensure_topic_exists()
        
        # Fetch and cache cluster metadata
        self._update_cluster_metadata()
        
        logger.info(f"StreamSocialEventProducer initialized with bootstrap servers: {self.config.bootstrap_servers}")
    
    def _initialize_producer(self) -> KafkaProducer:
        """Initialize KafkaProducer with cluster-aware settings."""
        return KafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            
            # Durability settings for cluster
            acks=self.config.acks,  # Wait for all in-sync replicas
            retries=self.config.retries,
            
            # Performance settings
            batch_size=self.config.batch_size,
            linger_ms=self.config.linger_ms,
            compression_type=self.config.compression_type,
            
            # Network settings
            request_timeout_ms=self.config.request_timeout_ms,
            max_in_flight_requests_per_connection=self.config.max_in_flight_requests,
            
            # Retry settings
            retry_backoff_ms=self.config.retry_backoff_ms,
        )
    
    def _initialize_admin_client(self) -> KafkaAdminClient:
        """Initialize KafkaAdminClient for cluster management."""
        return KafkaAdminClient(
            bootstrap_servers=self.config.bootstrap_servers,
            request_timeout_ms=self.config.request_timeout_ms,
        )
    
    def _ensure_topic_exists(self) -> None:
        """Create topic if it doesn't exist with cluster-aware configuration."""
        try:
            # Check if topic exists
            metadata = self.producer.topics()
            if self.topic in metadata:
                logger.info(f"Topic '{self.topic}' already exists")
                return
            
            # Create topic with cluster-aware settings
            topic = NewTopic(
                name=self.topic,
                num_partitions=self.config.partitions,
                replication_factor=self.config.replication_factor,
                topic_configs={
                    'min.insync.replicas': str(self.config.min_insync_replicas),
                    'compression.type': self.config.compression_type,
                    'retention.ms': str(RETENTION_MS),
                }
            )
            
            topic_futures = self.admin_client.create_topics([topic], validate_only=False)
            for topic_name, topic_future in topic_futures.items():
                try:
                    topic_future.result()
                    logger.info(f"Topic '{topic_name}' created successfully")
                except Exception as e:
                    logger.warning(f"Topic creation failed or already exists: {e}")
        except Exception as e:
            logger.error(f"Error ensuring topic exists: {e}")
    
    def _update_cluster_metadata(self) -> None:
        """Fetch and cache cluster metadata."""
        try:
            # Refresh metadata by accessing topics
            _ = self.producer.topics()
            logger.info("Cluster metadata updated successfully")
        except Exception as e:
            logger.warning(f"Could not fetch cluster metadata: {e}")
    
    def _get_partition_for_user(self, user_id: str) -> Optional[int]:
        """
        Determine partition for user_id to maintain ordering.
        
        Messages from the same user go to the same partition, ensuring
        ordering guarantees for user-specific events. Uses deterministic
        hashing to ensure consistent partitioning across processes.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Partition number or None for default behavior
        """
        try:
            partitions = self.producer.partitions_for_topic(self.topic)
            if partitions:
                # Use deterministic SHA256 hash for consistent partitioning across processes
                hash_value = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
                partition = hash_value % len(partitions)
                return partition
        except Exception as e:
            logger.warning(f"Could not determine partition: {e}")
        return None
    
    def publish_event(
        self,
        event_type: EventType,
        user_id: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        Publish an event to the cluster with proper error handling.
        
        Args:
            event_type: Type of the event
            user_id: ID of the user triggering the event
            data: Event-specific payload
            session_id: Optional session identifier
            callback: Optional callback function for async send
            
        Returns:
            event_id of the published event
            
        Raises:
            KafkaError: If the event cannot be published after retries
        """
        event = StreamSocialEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            data=data
        )
        
        start_time = time.time()
        
        try:
            # Use partition-aware send for ordering
            partition = self._get_partition_for_user(user_id)
            
            # Send with callback for async handling
            future = self.producer.send(
                self.topic,
                key=event.user_id,
                value=event.model_dump(),
                partition=partition
            )
            
            # Optional callback for async processing
            if callback:
                future.add_callback(callback)
                future.add_errback(self._send_error_callback)
            else:
                # Synchronous wait for confirmation
                future.get(timeout=self.config.request_timeout_ms / 1000)
            
            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self._metrics['messages_sent'] += 1
            self._metrics['send_latency_ms'].append(latency_ms)
            
            logger.debug(
                f"Event published: {event.event_id} (user: {user_id}, "
                f"type: {event_type}, latency: {latency_ms:.2f}ms)"
            )
            
            return event.event_id
            
        except KafkaError as e:
            self._metrics['messages_failed'] += 1
            logger.error(f"Failed to publish event for user {user_id}: {e}")
            raise
        except Exception as e:
            self._metrics['messages_failed'] += 1
            logger.error(f"Unexpected error publishing event: {e}")
            raise
    
    def _send_error_callback(self, exc: Exception) -> None:
        """Handle send errors in async mode."""
        logger.error(f"Async send error: {exc}")
        self._metrics['messages_failed'] += 1
    
    def publish_batch(self, events: List[Dict[str, Any]]) -> List[str]:
        """
        Publish multiple events in batch.
        
        Args:
            events: List of event dicts with keys: event_type, user_id, data, session_id (optional)
            
        Returns:
            List of event IDs
        """
        event_ids = []
        for i, event_data in enumerate(events):
            try:
                # Validate event_type exists
                event_type_str = event_data.get('event_type')
                if not event_type_str:
                    logger.error(f"Event {i}: Missing event_type field")
                    continue
                
                try:
                    event_type = EventType[event_type_str]
                except KeyError:
                    valid_types = [e.name for e in EventType]
                    logger.error(f"Event {i}: Invalid event_type '{event_type_str}'. Valid types: {valid_types}")
                    continue
                
                event_id = self.publish_event(
                    event_type=event_type,
                    user_id=event_data['user_id'],
                    data=event_data['data'],
                    session_id=event_data.get('session_id'),
                )
                event_ids.append(event_id)
            except KeyError as e:
                logger.error(f"Event {i}: Missing required field: {e}")
            except Exception as e:
                logger.error(f"Event {i}: Failed to publish event: {e}")
        
        # Ensure all messages are flushed
        self.flush()
        return event_ids
    
    def flush(self, timeout: Optional[float] = None) -> None:
        """
        Flush pending messages to the cluster.
        
        Args:
            timeout: Timeout in seconds (defaults to config request_timeout_ms)
        """
        timeout = timeout or (self.config.request_timeout_ms / 1000)
        self.producer.flush(timeout=timeout)
        logger.debug("Producer messages flushed to cluster")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get producer metrics.
        
        Returns:
            Dictionary with metrics including sent count, failed count, and latency stats
        """
        if self._metrics['send_latency_ms']:
            avg_latency = sum(self._metrics['send_latency_ms']) / len(self._metrics['send_latency_ms'])
            max_latency = max(self._metrics['send_latency_ms'])
            min_latency = min(self._metrics['send_latency_ms'])
        else:
            avg_latency = max_latency = min_latency = 0
        
        return {
            'messages_sent': self._metrics['messages_sent'],
            'messages_failed': self._metrics['messages_failed'],
            'avg_latency_ms': avg_latency,
            'max_latency_ms': max_latency,
            'min_latency_ms': min_latency,
            'bootstrap_servers': self.config.bootstrap_servers,
            'topic': self.topic,
        }
    
    def check_cluster_health(self) -> Dict[str, Any]:
        """
        Check the health of the Kafka cluster.
        
        Returns:
            Dictionary with cluster health information
        """
        try:
            self._update_cluster_metadata()
            
            # Get available topics and partitions
            topics = self.producer.topics()
            partitions = self.producer.partitions_for_topic(self.topic)
            
            return {
                'status': 'healthy',
                'topics_available': len(topics),
                'topic': self.topic,
                'partitions': len(partitions) if partitions else 0,
                'bootstrap_servers': self.config.bootstrap_servers,
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error checking cluster health: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    
    def close(self) -> None:
        """Close the producer and clean up resources."""
        try:
            self.flush()
            self.producer.close()
            self.admin_client.close()
            logger.info("StreamSocialEventProducer closed successfully")
        except Exception as e:
            logger.error(f"Error closing producer: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


        