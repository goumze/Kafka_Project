"""
Standalone consumer worker entrypoint.

Run multiple containers with the same CONSUMER_GROUP so Kafka assigns
partitions across replicas:

  python -m workers.consumer_worker
  docker compose ... up --scale kafka-consumer=3
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Optional

from config.settings import get_settings
from config.topic_bootstrap import try_ensure_topics_exist
from consumers.event_consumer import StreamSocialEventConsumer


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    settings = get_settings()
    _configure_logging(settings.log_level)
    log = logging.getLogger("streamsocial.worker")

    # Ensure topics exist before consuming
    if not try_ensure_topics_exist(settings=settings):
        log.warning("Topic bootstrap failed (will retry via consume)")

    consumer = StreamSocialEventConsumer(
        bootstrap_servers=settings.bootstrap_servers,
        group_id=settings.consumer_group_id,
        instance_id=settings.consumer_instance_id,
        auto_offset_reset=settings.consumer_auto_offset_reset,
        processing_delay_ms=settings.consumer_processing_delay_ms,
        max_poll_records=settings.consumer_max_poll_records,
        settings=settings,
    )

    def _handle_signal(signum: int, _frame: Optional[object]) -> None:
        log.info("Received signal %s — stopping consumer", signum)
        consumer.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    def handle_user_registration(event_data: dict) -> None:
        log.debug(
            "user_registration username=%s",
            event_data.get("data", {}).get("username"),
        )

    def handle_content_like(event_data: dict) -> None:
        log.debug("content_like user_id=%s", event_data.get("user_id"))

    consumer.register_handler("user_registration", handle_user_registration)
    consumer.register_handler("content_like", handle_content_like)

    log.info(
        "Starting consumer worker instance_id=%s group_id=%s brokers=%s "
        "delay_ms=%s max_poll_records=%s (scale replicas share group_id)",
        settings.consumer_instance_id,
        settings.consumer_group_id,
        settings.bootstrap_servers,
        settings.consumer_processing_delay_ms,
        settings.consumer_max_poll_records,
    )

    try:
        consumer.start_consuming()
    except Exception:
        log.exception("Consumer worker crashed")
        return 1
    finally:
        consumer.close()
        # small grace for log flush
        time.sleep(0.1)

    log.info("Consumer worker exited cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
