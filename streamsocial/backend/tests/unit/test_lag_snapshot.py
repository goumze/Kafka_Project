"""Lag snapshot serialization and pure lag math tests (no broker required)."""

from kafka import KafkaConsumer, TopicPartition

from metrics.lag_service import (
    LagSnapshot,
    build_lag_by_topic,
    build_lag_probe_kwargs,
    committed_offset_from_meta,
    partition_lag,
)


def test_lag_snapshot_to_dict():
    snap = LagSnapshot(
        group_id="g",
        total_lag=42,
        lag_by_topic={"user-actions": {"0": {"lag": 42}}},
        partition_count=1,
    )
    d = snap.to_dict()
    assert d["total_lag"] == 42
    assert d["group_id"] == "g"
    assert "timestamp" in d


def test_partition_lag_and_committed_meta():
    assert partition_lag(100, 40) == 60
    assert partition_lag(10, 50) == 0
    assert committed_offset_from_meta(None) == 0
    assert committed_offset_from_meta(-1) == 0
    assert committed_offset_from_meta(12) == 12

    class Meta:
        offset = 7

    assert committed_offset_from_meta(Meta()) == 7


def test_build_lag_by_topic():
    topic_partitions = {"user-actions": [0, 1], "system-events": [0]}
    end_offsets = {
        TopicPartition("user-actions", 0): 100,
        TopicPartition("user-actions", 1): 50,
        TopicPartition("system-events", 0): 10,
    }
    committed = {
        TopicPartition("user-actions", 0): 80,
        TopicPartition("user-actions", 1): None,
        TopicPartition("system-events", 0): 10,
    }
    lag_by_topic, total, count = build_lag_by_topic(
        topic_partitions, end_offsets, committed
    )
    assert count == 3
    assert total == 20 + 50 + 0
    assert lag_by_topic["user-actions"]["0"]["lag"] == 20
    assert lag_by_topic["user-actions"]["1"]["lag"] == 50
    assert lag_by_topic["system-events"]["0"]["lag"] == 0


def test_build_lag_probe_kwargs_non_member_and_compatible():
    """Probe must not join CONSUMER_GROUP and must use kafka-python-safe configs."""
    kwargs = build_lag_probe_kwargs(
        ["kafka-1:29092", "kafka-2:29092"],
        "streamsocial-lag-probe-test",
    )
    assert "group_id" not in kwargs
    assert "api_version_auto_timeout_ms" not in kwargs
    assert kwargs["bootstrap_servers"] == ["kafka-1:29092", "kafka-2:29092"]
    assert kwargs["client_id"] == "streamsocial-lag-probe-test"
    assert kwargs.get("enable_auto_commit") is False

    defaults = getattr(KafkaConsumer, "DEFAULT_CONFIG", {}) or {}
    if defaults:
        unknown = set(kwargs) - set(defaults)
        assert not unknown, f"unrecognized consumer configs: {unknown}"
