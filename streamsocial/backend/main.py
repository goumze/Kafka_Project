"""
StreamSocial FastAPI entrypoint (API + producer path).

Consumers run as separate worker processes by default so they can be
horizontally scaled with Docker Compose. Set API_EMBED_CONSUMER=true to
embed a single background consumer (local dev only).
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from config.topic_bootstrap import try_ensure_topics_exist
from controllers import (
    cluster_router,
    consumer_controller,
    consumer_router,
    event_controller,
    event_router,
    health_router,
    metrics_controller,
    metrics_router,
)
from consumers.event_consumer import StreamSocialEventConsumer
from producers.event_producer import StreamSocialEventProducer
from services.embedded_consumer_service import embedded_consumer_service
from services.lag_query_service import LagQueryService

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("streamsocial.api")

app = FastAPI(
    title="StreamSocial Backend API",
    version="2.0.0",
    description=(
        "Kafka scale demo: produce load, observe consumer lag via /metrics and "
        "/consumer/lag, scale kafka-consumer replicas to drain lag."
    ),
)

# Defer topic bootstrap to startup so import works offline
producer = StreamSocialEventProducer(settings=settings, ensure_topics=False)
event_controller.set_producer(producer)
event_controller.set_consumer(None)

lag_query = LagQueryService(settings=settings)
event_controller.set_lag_query_service(lag_query)
consumer_controller.set_lag_query_service(lag_query)
metrics_controller.set_lag_query_service(lag_query)
consumer_controller.set_embedded_service(embedded_consumer_service)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(event_router)
app.include_router(consumer_router)
app.include_router(cluster_router)
app.include_router(metrics_router)

# Optional embedded consumer (disabled by default for Compose scale demos)
_embedded_consumer: Optional[StreamSocialEventConsumer] = None
_embedded_thread: Optional[threading.Thread] = None
_embedded_running = False


def _run_embedded_consumer() -> None:
    global _embedded_consumer, _embedded_running
    try:
        _embedded_consumer = StreamSocialEventConsumer(
            settings=settings,
            instance_id=f"api-embedded-{settings.consumer_instance_id}",
        )
        _embedded_running = True
        event_controller.set_consumer(_embedded_consumer)
        embedded_consumer_service.set_state(
            _embedded_consumer,
            _embedded_thread,
            _embedded_running,
            instance_id=_embedded_consumer.instance_id,
        )
        consumer_controller.set_consumer_state(
            _embedded_consumer,
            _embedded_thread,
            _embedded_running,
            instance_id=_embedded_consumer.instance_id,
        )
        logger.warning(
            "Embedded consumer started (API_EMBED_CONSUMER=true). "
            "Prefer separate kafka-consumer containers for horizontal scale."
        )
        _embedded_consumer.start_consuming()
    except Exception:
        logger.exception("Embedded consumer failed")
        _embedded_running = False
        embedded_consumer_service.set_running(False)


@app.on_event("startup")
async def startup_event() -> None:
    global _embedded_thread
    logger.info(
        "API startup brokers=%s group_id=%s embed_consumer=%s",
        settings.bootstrap_servers,
        settings.consumer_group_id,
        settings.api_embed_consumer,
    )
    if not try_ensure_topics_exist(settings=settings):
        logger.warning("Topic bootstrap on API startup failed (brokers may be unavailable)")

    if settings.api_embed_consumer:
        _embedded_thread = threading.Thread(target=_run_embedded_consumer, daemon=True)
        _embedded_thread.start()
    else:
        logger.info(
            "Consumer not embedded. Scale workers: "
            "docker compose -f docker-compose.yml -f docker-compose.backend.yml "
            "up --scale kafka-consumer=3"
        )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _embedded_running
    _embedded_running = False
    if _embedded_consumer is not None:
        _embedded_consumer.stop()
        _embedded_consumer.close()
    try:
        producer.close()
    except Exception:
        logger.exception("Producer close failed")
    logger.info("API shutdown complete")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
