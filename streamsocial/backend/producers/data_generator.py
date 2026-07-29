"""
StreamSocial Data Generator
Generates realistic high-volume event streams for load testing and lag demonstration.

Features:
- Configurable event generation rate (events/sec)
- Multiple event type distributions
- Realistic user/content IDs
- Throughput measurement and reporting
"""

import time
import uuid
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
import threading
import json

from models.events import EventType
from producers.event_producer import StreamSocialEventProducer


@dataclass
class GenerationConfig:
    """Configuration for event generation"""
    events_per_second: int = 1000  # Target rate
    duration_seconds: int = 60     # How long to generate
    event_type_distribution: Dict[EventType, float] = None  # Probability distribution
    num_unique_users: int = 10000
    num_unique_content: int = 50000
    
    def __post_init__(self):
        """Set default distribution if not provided"""
        if self.event_type_distribution is None:
            # Realistic distribution for StreamSocial
            self.event_type_distribution = {
                EventType.USER_POST_CREATE: 0.05,
                EventType.USER_FOLLOW: 0.05,
                EventType.CONTENT_VIEW: 0.40,
                EventType.CONTENT_LIKE: 0.25,
                EventType.CONTENT_COMMENT: 0.10,
                EventType.CONTENT_SHARE: 0.05,
                EventType.USER_LOGIN: 0.05,
                EventType.SYSTEM_HEALTH_CHECK: 0.05,
            }


class StreamSocialDataGenerator:
    """
    Generates realistic event streams for testing and demonstration.
    
    Usage:
        generator = StreamSocialDataGenerator()
        config = GenerationConfig(
            events_per_second=5000,
            duration_seconds=120,
            num_unique_users=50000
        )
        stats = generator.generate(config)
        print(f"Generated {stats['total_events']} events at {stats['avg_throughput']:.0f} events/sec")
    """
    
    def __init__(self, bootstrap_servers: List[str] = None):
        """
        Initialize the data generator.
        
        Args:
            bootstrap_servers: Kafka broker addresses
        """
        self.producer = StreamSocialEventProducer(bootstrap_servers=bootstrap_servers)
        self.stats = {
            'total_events': 0,
            'events_by_type': {},
            'start_time': None,
            'end_time': None,
            'errors': 0,
        }
    
    def generate(self, config: GenerationConfig) -> Dict[str, Any]:
        """
        Generate events according to configuration.
        
        Args:
            config: GenerationConfig with rate, duration, and distribution
            
        Returns:
            Dictionary with generation statistics
        """
        self.stats = {
            'total_events': 0,
            'events_by_type': {},
            'start_time': datetime.now(),
            'end_time': None,
            'errors': 0,
            'duration_seconds': config.duration_seconds,
        }
        
        print(f"[GENERATOR] Starting event generation")
        print(f"[GENERATOR] Target rate: {config.events_per_second} events/sec")
        print(f"[GENERATOR] Duration: {config.duration_seconds} seconds")
        print(f"[GENERATOR] Expected total: ~{config.events_per_second * config.duration_seconds:,} events")
        print(f"[GENERATOR] Unique users: {config.num_unique_users:,}")
        print(f"[GENERATOR] Unique content: {config.num_unique_content:,}")
        
        # Pre-generate user and content IDs for realism
        user_ids = [f"user_{i}" for i in range(config.num_unique_users)]
        content_ids = [f"content_{i}" for i in range(config.num_unique_content)]
        
        # Calculate timing
        interval = 1.0 / config.events_per_second  # Time between events
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        events_in_batch = 0
        batch_start = time.time()
        
        print("[GENERATOR] Generating events...")
        
        try:
            while time.time() < end_time:
                # Select event type based on distribution
                event_type = self._select_event_type(config.event_type_distribution)
                
                # Generate event data
                user_id = random.choice(user_ids)
                content_id = random.choice(content_ids) if self._needs_content_id(event_type) else None
                data = self._generate_event_data(event_type, content_id)
                
                # Publish event
                try:
                    self.producer.publish_event(
                        event_type=event_type,
                        user_id=user_id,
                        data=data,
                        content_id=content_id
                    )
                    self.stats['total_events'] += 1
                    self.stats['events_by_type'][event_type.value] = \
                        self.stats['events_by_type'].get(event_type.value, 0) + 1
                    events_in_batch += 1
                except Exception as e:
                    self.stats['errors'] += 1
                    print(f"[ERROR] Failed to publish event: {e}")
                
                # Rate limiting
                elapsed = time.time() - batch_start
                expected_elapsed = events_in_batch * interval
                if elapsed < expected_elapsed:
                    time.sleep(expected_elapsed - elapsed)
                
                # Progress reporting every 10k events
                if self.stats['total_events'] % 10000 == 0:
                    current_time = time.time()
                    actual_rate = self.stats['total_events'] / (current_time - start_time)
                    print(f"[GENERATOR] {self.stats['total_events']:,} events sent "
                          f"({actual_rate:.0f} events/sec)")
            
            # Flush remaining messages
            self.producer.flush()
            
        except KeyboardInterrupt:
            print("[GENERATOR] Generation interrupted by user")
        
        self.stats['end_time'] = datetime.now()
        self._print_stats()
        return self._get_stats_summary()
    
    def generate_async(self, config: GenerationConfig) -> threading.Thread:
        """
        Generate events in a background thread.
        
        Args:
            config: GenerationConfig
            
        Returns:
            Thread object running the generation
        """
        thread = threading.Thread(target=self.generate, args=(config,), daemon=True)
        thread.start()
        return thread
    
    def _select_event_type(self, distribution: Dict[EventType, float]) -> EventType:
        """Select an event type based on distribution probabilities"""
        event_types = list(distribution.keys())
        probabilities = list(distribution.values())
        return random.choices(event_types, weights=probabilities, k=1)[0]
    
    def _needs_content_id(self, event_type: EventType) -> bool:
        """Check if event type requires content_id"""
        content_events = {
            EventType.CONTENT_VIEW,
            EventType.CONTENT_LIKE,
            EventType.CONTENT_COMMENT,
            EventType.CONTENT_SHARE,
            EventType.CONTENT_BOOKMARK,
            EventType.CONTENT_ANALYTICS,
        }
        return event_type in content_events
    
    def _generate_event_data(self, event_type: EventType, content_id: Optional[str]) -> Dict[str, Any]:
        """Generate realistic event payload based on event type"""
        
        event_data_generators = {
            EventType.USER_LOGIN: lambda: {
                "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "device_type": random.choice(["web", "mobile", "tablet"]),
                "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
            },
            EventType.USER_POST_CREATE: lambda: {
                "post_id": str(uuid.uuid4()),
                "content": f"Sample post content {random.randint(1, 1000)}",
                "media_count": random.randint(0, 5),
                "tags": [f"tag_{i}" for i in range(random.randint(0, 3))],
            },
            EventType.USER_FOLLOW: lambda: {
                "followed_user_id": f"user_{random.randint(0, 100000)}",
                "is_mutual": random.choice([True, False]),
            },
            EventType.CONTENT_VIEW: lambda: {
                "content_id": content_id,
                "watch_duration_sec": random.randint(1, 300),
                "completed": random.random() > 0.3,
            },
            EventType.CONTENT_LIKE: lambda: {
                "content_id": content_id,
                "liked": random.choice([True, False]),
            },
            EventType.CONTENT_COMMENT: lambda: {
                "content_id": content_id,
                "comment_id": str(uuid.uuid4()),
                "text": f"Comment #{random.randint(1, 1000)}",
                "reply_to_comment_id": str(uuid.uuid4()) if random.random() > 0.7 else None,
            },
            EventType.CONTENT_SHARE: lambda: {
                "content_id": content_id,
                "platform": random.choice(["twitter", "facebook", "email", "link"]),
                "shared_with_followers": random.choice([True, False]),
            },
            EventType.SYSTEM_HEALTH_CHECK: lambda: {
                "service": random.choice(["auth", "api", "database", "cache"]),
                "status": random.choice(["healthy", "degraded", "unhealthy"]),
                "response_time_ms": random.randint(10, 5000),
            },
        }
        
        generator = event_data_generators.get(event_type, lambda: {"generated_at": datetime.now().isoformat()})
        return generator()
    
    def _print_stats(self):
        """Print generation statistics"""
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            avg_throughput = self.stats['total_events'] / duration if duration > 0 else 0
            
            print("\n" + "="*70)
            print("EVENT GENERATION STATISTICS")
            print("="*70)
            print(f"Total Events Generated: {self.stats['total_events']:,}")
            print(f"Duration: {duration:.2f} seconds")
            print(f"Average Throughput: {avg_throughput:.0f} events/sec")
            print(f"Errors: {self.stats['errors']}")
            print("\nBreakdown by Event Type:")
            for event_type, count in sorted(self.stats['events_by_type'].items(), 
                                           key=lambda x: x[1], reverse=True):
                pct = (count / self.stats['total_events'] * 100) if self.stats['total_events'] > 0 else 0
                print(f"  {event_type:30} {count:10,} ({pct:5.1f}%)")
            print("="*70 + "\n")
    
    def _get_stats_summary(self) -> Dict[str, Any]:
        """Get summary statistics dictionary"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds() if self.stats['end_time'] else 0
        return {
            'total_events': self.stats['total_events'],
            'duration_seconds': duration,
            'avg_throughput': self.stats['total_events'] / duration if duration > 0 else 0,
            'errors': self.stats['errors'],
            'events_by_type': self.stats['events_by_type'],
        }
    
    def close(self):
        """Close the producer"""
        self.producer.close()
