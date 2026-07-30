"""
Background bulk event generation for lag demos.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, field_validator

from config.settings import get_settings
from producers.data_generator import GenerationConfig, StreamSocialDataGenerator

logger = logging.getLogger("streamsocial.loadgen")


class LoadGenRequest(BaseModel):
    """Validated load-generation parameters (shared by HTTP and service)."""

    events_per_second: int = Field(default=2000, ge=1, le=100000)
    duration_seconds: int = Field(default=30, ge=1, le=3600)
    num_unique_users: int = Field(default=10000, ge=1)
    num_unique_content: int = Field(default=50000, ge=1)
    burst_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=100000,
        description="Events per publish burst before rate pacing (defaults to LOADGEN_BURST_SIZE)",
    )
    background: bool = Field(
        default=True,
        description="Run loadgen in background so the HTTP call returns immediately",
    )

    @field_validator("events_per_second", "duration_seconds")
    @classmethod
    def _positive_rates(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be >= 1")
        return value

    def to_generation_config(self) -> GenerationConfig:
        burst = self.burst_size
        if burst is None:
            burst = get_settings().loadgen_burst_size
        return GenerationConfig(
            events_per_second=self.events_per_second,
            duration_seconds=self.duration_seconds,
            num_unique_users=self.num_unique_users,
            num_unique_content=self.num_unique_content,
            burst_size=burst,
        )


def validate_loadgen_dict(data: Dict[str, Any]) -> LoadGenRequest:
    """Validate a raw dict into LoadGenRequest (unit-test friendly)."""
    return LoadGenRequest.model_validate(data)


class LoadGenerationService:
    """Owns loadgen thread lifecycle and last-run stats."""

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stats: Dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def last_stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> Dict[str, Any]:
        return {"running": self.is_running(), "last_stats": self.last_stats}

    def start_background(self, config: GenerationConfig) -> Dict[str, Any]:
        with self._lock:
            if self.is_running():
                return {
                    "success": False,
                    "error": "Load generation already running",
                    "last_stats": self.last_stats,
                }
            self._thread = threading.Thread(
                target=self._run,
                args=(config,),
                daemon=True,
                name="streamsocial-loadgen",
            )
            self._thread.start()
            logger.info(
                "loadgen_started eps=%s duration=%s users=%s content=%s",
                config.events_per_second,
                config.duration_seconds,
                config.num_unique_users,
                config.num_unique_content,
            )
            return {
                "success": True,
                "message": "Background load generation started",
                "config": {
                    "events_per_second": config.events_per_second,
                    "duration_seconds": config.duration_seconds,
                    "num_unique_users": config.num_unique_users,
                    "num_unique_content": config.num_unique_content,
                },
                "observe_lag": {
                    "metrics": "GET /metrics",
                    "consumer_lag": "GET /consumer/lag",
                },
            }

    def run_sync(self, config: GenerationConfig) -> Dict[str, Any]:
        try:
            stats = self._run(config)
            return {
                "success": True,
                "message": f"Generated {stats['total_events']:,} events",
                "statistics": {
                    "total_events": stats["total_events"],
                    "duration_seconds": stats["duration_seconds"],
                    "average_throughput": stats["avg_throughput"],
                    "errors": stats["errors"],
                    "events_by_type": stats["events_by_type"],
                },
            }
        except Exception as exc:
            logger.exception("Synchronous load generation failed")
            return {"success": False, "error": str(exc)}

    def generate(
        self, request: Union[LoadGenRequest, GenerationConfig]
    ) -> Dict[str, Any]:
        if isinstance(request, LoadGenRequest):
            config = request.to_generation_config()
            background = request.background
        else:
            config = request
            background = True
        if background:
            return self.start_background(config)
        return self.run_sync(config)

    def _run(self, config: GenerationConfig) -> Dict[str, Any]:
        generator = StreamSocialDataGenerator()
        try:
            stats = generator.generate(config)
            with self._lock:
                self._stats = stats
            logger.info(
                "loadgen_finished total_events=%s avg_throughput=%s errors=%s",
                stats.get("total_events"),
                stats.get("avg_throughput"),
                stats.get("errors"),
            )
            return stats
        finally:
            generator.close()
