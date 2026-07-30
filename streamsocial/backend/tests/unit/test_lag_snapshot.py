"""Lag snapshot serialization and pure lag math tests (no broker required)."""

from kafka import TopicPartition

from metrics.lag_service import (
    LagSnapshot,
    build_lag_by_topic,
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
