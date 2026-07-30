"""Pure unit tests for topic bootstrap planning (no Kafka)."""

from config.settings import Settings
from config.topic_bootstrap import planned_topic_specs, topic_names


def _settings() -> Settings:
    return Settings(
        kafka_brokers=["localhost:9092"],
        partitions_user_actions=8,
        partitions_content_interactions=4,
        partitions_system_events=2,
        replication_factor=1,
    )


def test_planned_topic_specs_names_and_partitions():
    specs = planned_topic_specs(_settings())
    by_name = {s["name"]: s for s in specs}
    assert set(by_name) == {
        "user-actions",
        "content-interactions",
        "system-events",
    }
    assert by_name["user-actions"]["num_partitions"] == 8
    assert by_name["content-interactions"]["num_partitions"] == 4
    assert by_name["system-events"]["num_partitions"] == 2
    assert by_name["user-actions"]["replication_factor"] == 1


def test_topic_names_order_stable():
    names = topic_names(_settings())
    assert "user-actions" in names
    assert len(names) == 3
