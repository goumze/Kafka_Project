"""API health/root without live Kafka (TestClient + mocked lag)."""

from typing import Any, Dict, Optional

from fastapi.testclient import TestClient

from metrics.lag_service import LagSnapshot
from services.lag_query_service import LagQueryService


class _FakeLagBackend:
    def get_lag(self, topics: Optional[list] = None) -> LagSnapshot:
        return LagSnapshot(
            group_id="streamsocial_event_consumers",
            total_lag=0,
            lag_by_topic={},
            partition_count=0,
        )


def test_health_and_root_no_kafka():
    # Import app after env is quiet; producer is lazy
    import main
    from controllers import consumer_controller, event_controller, metrics_controller

    fake = LagQueryService(lag_service=_FakeLagBackend())  # type: ignore[arg-type]
    consumer_controller.set_lag_query_service(fake)
    event_controller.set_lag_query_service(fake)
    metrics_controller.set_lag_query_service(fake)

    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

    root = client.get("/")
    assert root.status_code == 200
    body = root.json()
    assert body["kafka_integration"] == "enabled"
    assert "endpoints" in body


def test_consumer_start_disabled():
    import main
    from controllers import consumer_controller
    from services.lag_query_service import LagQueryService

    fake = LagQueryService(lag_service=_FakeLagBackend())  # type: ignore[arg-type]
    consumer_controller.set_lag_query_service(fake)

    client = TestClient(main.app)
    r = client.post("/consumer/start")
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"
