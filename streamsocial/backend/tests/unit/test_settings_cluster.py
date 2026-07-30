"""Settings env parsing for cluster ops and flags."""

from config.settings import Settings


def test_cluster_ops_env(monkeypatch):
    monkeypatch.setenv("CLUSTER_OPS_ENABLED", "true")
    monkeypatch.setenv("BROKER_CONTAINER_NAMES", "b1,b2")
    monkeypatch.setenv("PRIMARY_BROKER_CONTAINER", "b1")
    monkeypatch.setenv("CLUSTER_INTERNAL_BOOTSTRAP", "b1:29092")
    s = Settings.from_env()
    assert s.cluster_ops_enabled is True
    assert s.broker_container_names == ["b1", "b2"]
    assert s.primary_broker_container == "b1"
    assert s.cluster_internal_bootstrap == "b1:29092"


def test_api_embed_default_false(monkeypatch):
    monkeypatch.delenv("API_EMBED_CONSUMER", raising=False)
    s = Settings.from_env()
    assert s.api_embed_consumer is False


def test_consumer_instance_id_from_hostname(monkeypatch):
    monkeypatch.delenv("INSTANCE_ID", raising=False)
    monkeypatch.setenv("HOSTNAME", "kafka-consumer-2")
    s = Settings.from_env()
    assert s.consumer_instance_id == "kafka-consumer-2"


def test_loadgen_burst_env(monkeypatch):
    monkeypatch.setenv("LOADGEN_BURST_SIZE", "75")
    s = Settings.from_env()
    assert s.loadgen_burst_size == 75


def test_consumer_delay_default(monkeypatch):
    monkeypatch.delenv("CONSUMER_PROCESSING_DELAY_MS", raising=False)
    s = Settings.from_env()
    assert s.consumer_processing_delay_ms == 2.0
