"""
StreamSocial Event Consumer
Multi-topic consumer with group coordination, lag logging, and demo processing delay.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from kafka import KafkaConsumer, TopicPartition

from config.settings import Settings, get_settings
from config.topic_config import StreamSocialTopicManager

logger = logging.getLogger("streamsocial.consumer")


class StreamSocialEventConsumer:
    """
    Consumer for StreamSocial events from multiple topics.

    Designed for horizontal scale: many processes share group_id and
    Kafka assigns partitions across instances.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        auto_offset_reset: Optional[str] = None,
        processing_delay_ms: Optional[float] = None,
        max_poll_records: Optional[int] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.bootstrap_servers = bootstrap_servers or self.settings.bootstrap_servers
        self.group_id = group_id or self.settings.consumer_group_id
        self.instance_id = instance_id or self.settings.consumer_instance_id
        self.topic_manager = StreamSocialTopicManager(settings=self.settings)
        self.processing_delay_ms = (
            self.settings.consumer_processing_delay_ms
            if processing_delay_ms is None
            else processing_delay_ms
        )
        self._stop = False

        if topics is None:
            topics = self.topic_manager.get_all_topic_names()
        self.topics = topics

        self.consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            client_id=f"streamsocial-{self.instance_id}",
            auto_offset_reset=auto_offset_reset
            or self.settings.consumer_auto_offset_reset,
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else None,
            session_timeout_ms=self.settings.consumer_session_timeout_ms,
            max_poll_records=max_poll_records
            or self.settings.consumer_max_poll_records,
            max_poll_interval_ms=self.settings.consumer_max_poll_interval_ms,
        )

        self.event_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.processed_events: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {
            "total_events": 0,
            "events_by_type": defaultdict(int),
            "events_by_topic": defaultdict(int),
            "events_by_partition": defaultdict(int),
            "errors": 0,
            "handler_errors": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "assigned_partitions": set(),
        }
        self.partition_offsets: Dict[TopicPartition, Dict[str, int]] = {}
        self.lag_history: List[Dict[str, Any]] = []
        self._last_lag_log = 0.0

        logger.info(
            "Initialized consumer instance_id=%s group_id=%s topics=%s delay_ms=%s",
            self.instance_id,
            self.group_id,
            ",".join(self.topics),
            self.processing_delay_ms,
        )

    def stop(self) -> None:
        """Request cooperative shutdown of the consume loop."""
        self._stop = True

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], None],
    ) -> None:
        self.event_handlers[event_type] = handler
        logger.info(
            "Registered handler instance_id=%s event_type=%s",
            self.instance_id,
            event_type,
        )

    def start_consuming(self, max_messages: Optional[int] = None) -> None:
        message_count = 0
        self.stats["start_time"] = datetime.now()
        self._stop = False
        logger.info("Starting consumption instance_id=%s", self.instance_id)

        try:
            while not self._stop:
                polled = self.consumer.poll(timeout_ms=1000)
                if not polled:
                    self._maybe_log_lag()
                    continue

                for _tp, messages in polled.items():
                    for message in messages:
                        if self._stop:
                            break
                        try:
                            self._process_message(message)
                            message_count += 1
                            if max_messages and message_count >= max_messages:
                                self._stop = True
                                break
                        except Exception as exc:
                            self.stats["errors"] += 1
                            logger.error(
                                "Failed to process message instance_id=%s err=%s",
                                self.instance_id,
                                exc,
                            )
                    if self._stop:
                        break

                self._maybe_log_lag()

        except KeyboardInterrupt:
            logger.info(
                "KeyboardInterrupt after %s messages instance_id=%s",
                message_count,
                self.instance_id,
            )
        finally:
            self.stats["end_time"] = datetime.now()
            self._print_stats()

    def _process_message(self, message: Any) -> None:
        assigned: Set[Any] = self.stats["assigned_partitions"]
        assigned.add(f"{message.topic}-{message.partition}")

        event_data = message.value if message.value else {}
        event_type = event_data.get("event_type", "unknown")
        topic_name = message.topic
        partition = message.partition
        offset = message.offset

        self.stats["total_events"] += 1
        self.stats["events_by_type"][event_type] += 1
        self.stats["events_by_topic"][topic_name] += 1
        self.stats["events_by_partition"][f"{topic_name}-{partition}"] += 1

        if len(self.processed_events) >= 1000:
            self.processed_events.pop(0)

        self.processed_events.append(
            {
                **event_data,
                "processed_at": datetime.now().isoformat(),
                "topic": topic_name,
                "partition": partition,
                "offset": offset,
                "consumer_instance": self.instance_id,
            }
        )

        every = max(1, self.settings.consumer_log_every_n)
        if self.stats["total_events"] % every == 0:
            logger.info(
                "progress instance_id=%s events=%s last_topic=%s partition=%s offset=%s",
                self.instance_id,
                self.stats["total_events"],
                topic_name,
                partition,
                offset,
            )

        # Demo knob: artificial processing delay to induce consumer lag
        if self.processing_delay_ms and self.processing_delay_ms > 0:
            time.sleep(self.processing_delay_ms / 1000.0)

        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type](event_data)
            except Exception as handler_error:
                self.stats["handler_errors"] += 1
                logger.error(
                    "Handler error instance_id=%s type=%s err=%s",
                    self.instance_id,
                    event_type,
                    handler_error,
                )

    def _maybe_log_lag(self) -> None:
        interval = self.settings.consumer_lag_log_interval_sec
        now = time.time()
        if now - self._last_lag_log < interval:
            return
        self._last_lag_log = now
        try:
            lag_info = self.get_consumer_lag()
            total_lag = sum(
                v["lag"]
                for topic_lags in lag_info.values()
                for v in topic_lags.values()
            )
            assigned = len(self.stats["assigned_partitions"])
            logger.info(
                "lag_report instance_id=%s group_id=%s total_lag=%s assigned_partitions=%s events=%s",
                self.instance_id,
                self.group_id,
                total_lag,
                assigned,
                self.stats["total_events"],
            )
        except Exception as exc:
            logger.warning(
                "lag_report failed instance_id=%s err=%s", self.instance_id, exc
            )

    def get_consumer_lag(self) -> Dict[str, Dict[str, Any]]:
        """Lag for partitions currently assigned to this consumer instance."""
        lag_by_topic: Dict[str, Dict[str, Any]] = defaultdict(dict)

        try:
            assigned_partitions = self.consumer.assignment()
            if not assigned_partitions:
                return {}

            end_offsets = self.consumer.end_offsets(list(assigned_partitions))

            for tp in assigned_partitions:
                committed_meta = None
                try:
                    committed_meta = self.consumer.committed(tp)
                except Exception:
                    committed_meta = None

                if committed_meta is None:
                    committed_offset = 0
                elif hasattr(committed_meta, "offset"):
                    committed_offset = int(committed_meta.offset)
                else:
                    committed_offset = int(committed_meta)

                high_water_mark = int(end_offsets.get(tp, 0) or 0)
                lag = max(0, high_water_mark - committed_offset)

                lag_by_topic[tp.topic][str(tp.partition)] = {
                    "committed_offset": committed_offset,
                    "high_water_mark": high_water_mark,
                    "lag": lag,
                }
                self.partition_offsets[tp] = {
                    "committed": committed_offset,
                    "high_water_mark": high_water_mark,
                    "lag": lag,
                }

            total_lag = sum(
                v["lag"]
                for topic_lags in lag_by_topic.values()
                for v in topic_lags.values()
            )
            self.lag_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "total_lag": total_lag,
                    "by_topic": {k: dict(v) for k, v in lag_by_topic.items()},
                }
            )
            if len(self.lag_history) > 100:
                self.lag_history.pop(0)
        except Exception as exc:
            logger.error(
                "Failed to calculate lag instance_id=%s err=%s",
                self.instance_id,
                exc,
            )

        return {k: dict(v) for k, v in lag_by_topic.items()}

    def get_stats(self) -> Dict[str, Any]:
        end_time = self.stats["end_time"] or datetime.now()
        uptime = (end_time - self.stats["start_time"]).total_seconds()
        lag_info = self.get_consumer_lag()
        total_lag = sum(
            v["lag"] for topic_lags in lag_info.values() for v in topic_lags.values()
        )

        return {
            "consumer_instance": self.instance_id,
            "group_id": self.group_id,
            "total_events": self.stats["total_events"],
            "uptime_seconds": uptime,
            "throughput_events_per_sec": (
                self.stats["total_events"] / uptime if uptime > 0 else 0
            ),
            "events_by_type": dict(self.stats["events_by_type"]),
            "events_by_topic": dict(self.stats["events_by_topic"]),
            "assigned_partitions": len(self.stats["assigned_partitions"]),
            "total_lag": total_lag,
            "lag_by_topic": lag_info,
            "errors": self.stats["errors"],
            "handler_errors": self.stats["handler_errors"],
            "processing_delay_ms": self.processing_delay_ms,
            "recent_events": self.get_processed_events(limit=10),
        }

    def get_processed_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if limit:
            return self.processed_events[-limit:]
        return self.processed_events

    def _print_stats(self) -> None:
        stats = self.get_stats()
        logger.info(
            "shutdown_stats instance_id=%s events=%s uptime=%.2f throughput=%.0f lag=%s errors=%s",
            self.instance_id,
            stats["total_events"],
            stats["uptime_seconds"],
            stats["throughput_events_per_sec"],
            stats["total_lag"],
            stats["errors"],
        )

    def close(self) -> None:
        self._stop = True
        try:
            self.consumer.close()
            logger.info("Closed consumer instance_id=%s", self.instance_id)
        except Exception as exc:
            logger.error(
                "Error closing consumer instance_id=%s err=%s",
                self.instance_id,
                exc,
            )
