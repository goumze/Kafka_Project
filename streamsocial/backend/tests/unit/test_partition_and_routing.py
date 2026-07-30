"""Unit tests for partition keys and event-to-topic routing."""

from config.partition_strategy import PartitionStrategy
from config.settings import Settings
from config.topic_config import StreamSocialTopicManager, TopicType
from models.events import EventType, StreamSocialEvent


def _settings() -> Settings:
    return Settings(
        kafka_brokers=["localhost:9092"],
        partitions_user_actions=24,
        partitions_content_interactions=12,
        partitions_system_events=6,
        replication_factor=1,
    )


def test_event_model():
    event = StreamSocialEvent(
        event_id="test-123",
        event_type=EventType.USER_REGISTRATION,
        user_id="user-456",
        data={"username": "testuser"},
    )
    assert event.event_id == "test-123"
    assert event.event_type == EventType.USER_REGISTRATION
    assert event.user_id == "user-456"


def test_topic_routing():
    tm = StreamSocialTopicManager(_settings())
    assert tm.get_topic_for_event("user_registration") == TopicType.USER_ACTIONS
    assert tm.get_topic_for_event("content_like") == TopicType.CONTENT_INTERACTIONS
    assert tm.get_topic_for_event("system_health_check") == TopicType.SYSTEM_EVENTS
    assert tm.get_topic_for_event("unknown_thing") == TopicType.SYSTEM_EVENTS


def test_partition_stable_per_key():
    ps = PartitionStrategy(settings=_settings())
    a = ps.get_partition_for_user_action("user_42")
    b = ps.get_partition_for_user_action("user_42")
    assert a == b
    assert 0 <= a < 24


def test_partition_spreads_keys():
    ps = PartitionStrategy(settings=_settings())
    parts = {ps.get_partition_for_user_action(f"user_{i}") for i in range(200)}
    # With 24 partitions and 200 keys, expect multiple partitions used
    assert len(parts) > 5


def test_content_and_system_partitions():
    ps = PartitionStrategy(settings=_settings())
    c = ps.get_partition_for_content_interaction("content_9")
    s = ps.get_partition_for_system_event("auth")
    assert 0 <= c < 12
    assert 0 <= s < 6


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("KAFKA_BROKERS", "a:9092,b:9092")
    monkeypatch.setenv("CONSUMER_GROUP", "g1")
    monkeypatch.setenv("PARTITIONS_USER_ACTIONS", "8")
    s = Settings.from_env()
    assert s.kafka_brokers == ["a:9092", "b:9092"]
    assert s.consumer_group_id == "g1"
    assert s.partitions_user_actions == 8
