"""
StreamSocial Data Generator
Generates realistic high-volume event streams for load testing and lag demonstration.

Features:
- Configurable event generation rate (events/sec) with windowed burst pacing
- Multiple event type distributions
- Realistic user/content IDs
- Throughput measurement and reporting
"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import Settings, get_settings
from models.events import EventType
from producers.event_producer import StreamSocialEventProducer

logger = logging.getLogger("streamsocial.loadgen")


@dataclass
class GenerationConfig:
    """Configuration for event generation"""

    events_per_second: int = 1000  # Target rate
    duration_seconds: int = 60  # How long to generate
    event_type_distribution: Optional[Dict[EventType, float]] = None
    num_unique_users: int = 10000
    num_unique_content: int = 50000
    # Publish this many events before applying rate-limit sleep (higher = more throughput)
    burst_size: int = 50

    def __post_init__(self) -> None:
        """Set default distribution if not provided"""
        if self.event_type_distribution is None:
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
        if self.burst_size < 1:
            self.burst_size = 1


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
    """

    def __init__(
        self,
        bootstrap_servers: Optional[List[str]] = None,
        settings: Optional[Settings] = None,
        producer: Optional[StreamSocialEventProducer] = None,
    ):
        self.settings = settings or get_settings()
        self.producer = producer or StreamSocialEventProducer(
            bootstrap_servers=bootstrap_servers or self.settings.bootstrap_servers,
            settings=self.settings,
        )
        self.stats: Dict[str, Any] = {
            "total_events": 0,
            "events_by_type": {},
            "start_time": None,
            "end_time": None,
            "errors": 0,
        }

    def generate(self, config: GenerationConfig) -> Dict[str, Any]:
        """Generate events according to configuration (windowed burst pacing)."""
        self.stats = {
            "total_events": 0,
            "events_by_type": {},
            "start_time": datetime.now(),
            "end_time": None,
            "errors": 0,
            "duration_seconds": config.duration_seconds,
        }

        logger.info(
            "generator_start eps=%s duration=%s users=%s content=%s burst_size=%s",
            config.events_per_second,
            config.duration_seconds,
            config.num_unique_users,
            config.num_unique_content,
            config.burst_size,
        )
        print("[GENERATOR] Starting event generation")
        print(f"[GENERATOR] Target rate: {config.events_per_second} events/sec")
        print(f"[GENERATOR] Duration: {config.duration_seconds} seconds")
        print(
            f"[GENERATOR] Expected total: "
            f"~{config.events_per_second * config.duration_seconds:,} events"
        )
        print(f"[GENERATOR] Unique users: {config.num_unique_users:,}")
        print(f"[GENERATOR] Unique content: {config.num_unique_content:,}")
        print(f"[GENERATOR] Burst size: {config.burst_size}")

        user_ids = [f"user_{i}" for i in range(config.num_unique_users)]
        content_ids = [f"content_{i}" for i in range(config.num_unique_content)]

        start_time = time.time()
        end_time = start_time + config.duration_seconds
        # Window-based pacing: fill each 1s window up to events_per_second
        window_start = start_time
        window_count = 0
        target_per_window = max(1, config.events_per_second)
        burst_size = max(1, min(config.burst_size, target_per_window))

        print("[GENERATOR] Generating events...")

        try:
            while time.time() < end_time:
                # Emit a burst without per-message sleep
                for _ in range(burst_size):
                    if time.time() >= end_time:
                        break
                    if window_count >= target_per_window:
                        break

                    event_type = self._select_event_type(config.event_type_distribution)
                    user_id = random.choice(user_ids)
                    content_id = (
                        random.choice(content_ids)
                        if self._needs_content_id(event_type)
                        else None
                    )
                    data = self._generate_event_data(event_type, content_id)

                    try:
                        self.producer.publish_event(
                            event_type=event_type,
                            user_id=user_id,
                            data=data,
                            content_id=content_id,
                        )
                        self.stats["total_events"] += 1
                        self.stats["events_by_type"][event_type.value] = (
                            self.stats["events_by_type"].get(event_type.value, 0) + 1
                        )
                        window_count += 1
                    except Exception as exc:
                        self.stats["errors"] += 1
                        logger.warning("publish failed: %s", exc)
                        print(f"[ERROR] Failed to publish event: {exc}")

                now = time.time()
                # Pace to target rate once window is full
                if window_count >= target_per_window:
                    elapsed = now - window_start
                    if elapsed < 1.0:
                        time.sleep(1.0 - elapsed)
                    window_start = time.time()
                    window_count = 0
                elif now - window_start >= 1.0:
                    # Under-filled window (producer slower than target) — roll window
                    window_start = now
                    window_count = 0

                if (
                    self.stats["total_events"] > 0
                    and self.stats["total_events"] % 10000 == 0
                ):
                    current_time = time.time()
                    actual_rate = self.stats["total_events"] / max(
                        0.001, current_time - start_time
                    )
                    msg = (
                        f"[GENERATOR] {self.stats['total_events']:,} events sent "
                        f"({actual_rate:.0f} events/sec)"
                    )
                    print(msg)
                    logger.info(
                        "generator_progress events=%s rate=%.0f",
                        self.stats["total_events"],
                        actual_rate,
                    )

            self.producer.flush()

        except KeyboardInterrupt:
            print("[GENERATOR] Generation interrupted by user")
            logger.warning("generator interrupted")

        self.stats["end_time"] = datetime.now()
        self._print_stats()
        return self._get_stats_summary()

    def generate_async(self, config: GenerationConfig) -> threading.Thread:
        """Generate events in a background thread."""
        thread = threading.Thread(target=self.generate, args=(config,), daemon=True)
        thread.start()
        return thread

    def _select_event_type(self, distribution: Dict[EventType, float]) -> EventType:
        event_types = list(distribution.keys())
        probabilities = list(distribution.values())
        return random.choices(event_types, weights=probabilities, k=1)[0]

    def _needs_content_id(self, event_type: EventType) -> bool:
        content_events = {
            EventType.CONTENT_VIEW,
            EventType.CONTENT_LIKE,
            EventType.CONTENT_COMMENT,
            EventType.CONTENT_SHARE,
            EventType.CONTENT_BOOKMARK,
            EventType.CONTENT_ANALYTICS,
        }
        return event_type in content_events

    def _generate_event_data(
        self, event_type: EventType, content_id: Optional[str]
    ) -> Dict[str, Any]:
        event_data_generators = {
            EventType.USER_LOGIN: lambda: {
                "ip_address": (
                    f"{random.randint(1, 255)}.{random.randint(1, 255)}."
                    f"{random.randint(1, 255)}.{random.randint(1, 255)}"
                ),
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
                "reply_to_comment_id": (
                    str(uuid.uuid4()) if random.random() > 0.7 else None
                ),
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

        generator = event_data_generators.get(
            event_type, lambda: {"generated_at": datetime.now().isoformat()}
        )
        return generator()

    def _print_stats(self) -> None:
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()
            avg_throughput = (
                self.stats["total_events"] / duration if duration > 0 else 0
            )

            print("\n" + "=" * 70)
            print("EVENT GENERATION STATISTICS")
            print("=" * 70)
            print(f"Total Events Generated: {self.stats['total_events']:,}")
            print(f"Duration: {duration:.2f} seconds")
            print(f"Average Throughput: {avg_throughput:.0f} events/sec")
            print(f"Errors: {self.stats['errors']}")
            print("\nBreakdown by Event Type:")
            for event_type, count in sorted(
                self.stats["events_by_type"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                pct = (
                    (count / self.stats["total_events"] * 100)
                    if self.stats["total_events"] > 0
                    else 0
                )
                print(f"  {event_type:30} {count:10,} ({pct:5.1f}%)")
            print("=" * 70 + "\n")

    def _get_stats_summary(self) -> Dict[str, Any]:
        duration = (
            (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            if self.stats["end_time"]
            else 0
        )
        return {
            "total_events": self.stats["total_events"],
            "duration_seconds": duration,
            "avg_throughput": (
                self.stats["total_events"] / duration if duration > 0 else 0
            ),
            "errors": self.stats["errors"],
            "events_by_type": self.stats["events_by_type"],
        }

    def close(self) -> None:
        """Close the producer"""
        self.producer.close()
