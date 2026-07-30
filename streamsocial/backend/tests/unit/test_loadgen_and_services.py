"""Unit tests for loadgen validation, lag query facade, cluster allowlist."""

import pytest
from pydantic import ValidationError

from config.settings import Settings
from metrics.lag_service import LagSnapshot
from services.cluster_ops_service import ClusterOpsService
from services.lag_query_service import LagQueryService
from services.load_generation_service import (
    LoadGenerationService,
    LoadGenRequest,
    validate_loadgen_dict,
)


def test_loadgen_request_defaults():
    req = LoadGenRequest()
    assert req.events_per_second == 2000
    assert req.background is True
    cfg = req.to_generation_config()
    assert cfg.events_per_second == 2000
    assert cfg.duration_seconds == 30


def test_loadgen_request_rejects_zero_rate():
    with pytest.raises(ValidationError):
        LoadGenRequest(events_per_second=0)


def test_loadgen_request_rejects_too_long():
    with pytest.raises(ValidationError):
        LoadGenRequest(duration_seconds=99999)


def test_validate_loadgen_dict():
    req = validate_loadgen_dict(
        {"events_per_second": 100, "duration_seconds": 5, "background": False}
    )
    assert req.events_per_second == 100
    assert req.background is False


def test_loadgen_service_already_running(monkeypatch):
    svc = LoadGenerationService()

    class Alive:
        def is_alive(self):
            return True

    svc._thread = Alive()  # type: ignore[assignment]
    from producers.data_generator import GenerationConfig

    result = svc.start_background(GenerationConfig(events_per_second=10, duration_seconds=1))
    assert result["success"] is False
    assert "already running" in result["error"]


def test_lag_query_service_metrics_payload():
    class FakeLag:
        def get_lag(self, topics=None):
            return LagSnapshot(
                group_id="g",
                total_lag=7,
                lag_by_topic={"user-actions": {}},
                partition_count=2,
            )

    settings = Settings(
        kafka_brokers=["localhost:9092"],
        consumer_group_id="g",
        partitions_user_actions=3,
        partitions_content_interactions=2,
        partitions_system_events=1,
    )
    svc = LagQueryService(settings=settings, lag_service=FakeLag())  # type: ignore[arg-type]
    payload = svc.metrics_payload()
    assert payload["total_lag"] == 7
    assert payload["consumer_group_id"] == "g"
    assert payload["partitions"]["user-actions"] == 3
    assert "observed_at" in payload


def test_cluster_ops_disabled_by_default():
    settings = Settings(cluster_ops_enabled=False)
    ops = ClusterOpsService(settings=settings)
    result = ops.get_health()
    assert result["status"] == "disabled"


def test_cluster_ops_allowlist():
    settings = Settings(
        cluster_ops_enabled=True,
        broker_container_names=["kafka-broker-1", "kafka-broker-2"],
    )
    ops = ClusterOpsService(settings=settings)
    bad = ops.simulate_failure("not-a-broker")
    assert bad["status"] == "error"
    assert "Unknown broker" in bad["message"]



def test_loadgen_burst_from_request(monkeypatch):
    monkeypatch.setenv("LOADGEN_BURST_SIZE", "33")
    req = LoadGenRequest(events_per_second=100, duration_seconds=5, burst_size=12)
    cfg = req.to_generation_config()
    assert cfg.burst_size == 12

    req2 = LoadGenRequest(events_per_second=100, duration_seconds=5)
    cfg2 = req2.to_generation_config()
    assert cfg2.burst_size == 33
