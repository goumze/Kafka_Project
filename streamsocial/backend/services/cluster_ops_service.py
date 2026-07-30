"""
Demo cluster operations via local Docker CLI.

Requires docker socket access from the API container/host. Gated by
Settings.cluster_ops_enabled.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from config.settings import Settings, get_settings

logger = logging.getLogger("streamsocial.cluster_ops")


class ClusterOpsError(Exception):
    """Raised when cluster ops are disabled or input is invalid."""


class ClusterOpsService:
    """Allowlisted docker-based broker ops for the lag/fault demo."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.cluster_ops_enabled)

    @property
    def broker_containers(self) -> List[str]:
        return list(self.settings.broker_container_names)

    def _require_enabled(self) -> Optional[Dict[str, Any]]:
        if self.enabled:
            return None
        return {
            "status": "disabled",
            "message": (
                "Cluster docker ops disabled. Set CLUSTER_OPS_ENABLED=true "
                "and mount the docker socket if you need these demo endpoints."
            ),
            "timestamp": self._ts(),
        }

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _validate_broker(self, broker_name: str) -> None:
        allow = set(self.broker_containers)
        if broker_name not in allow:
            raise ClusterOpsError(
                f"Unknown broker: {broker_name}. Allowed: {sorted(allow)}"
            )

    def _run(
        self,
        args: Sequence[str],
        timeout: float = 5.0,
    ) -> subprocess.CompletedProcess[str]:
        logger.debug("cluster_ops_exec cmd=%s", " ".join(args))
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def get_health(self) -> Dict[str, Any]:
        blocked = self._require_enabled()
        if blocked:
            return blocked
        try:
            primary = self.settings.primary_broker_container
            internal = self.settings.cluster_internal_bootstrap
            probe = self._run(
                [
                    "docker",
                    "exec",
                    primary,
                    "kafka-broker-api-versions",
                    "--bootstrap-server",
                    internal,
                ],
                timeout=5,
            )
            broker_statuses: Dict[str, Any] = {}
            for i, container in enumerate(self.broker_containers, 1):
                try:
                    status_result = self._run(
                        [
                            "docker",
                            "ps",
                            "--filter",
                            f"name={container}",
                            "--format",
                            "{{.State}}",
                        ],
                        timeout=2,
                    )
                    broker_statuses[container] = {
                        "status": status_result.stdout.strip() or "unknown",
                        "broker_id": i,
                    }
                except Exception:
                    logger.exception("Failed to query broker container %s", container)
                    broker_statuses[container] = {
                        "status": "unknown",
                        "broker_id": i,
                    }

            healthy = sum(
                1 for b in broker_statuses.values() if b.get("status") == "running"
            )
            return {
                "status": "healthy" if healthy >= 2 else "degraded",
                "brokers": broker_statuses,
                "healthy_count": healthy,
                "total_brokers": len(self.broker_containers),
                "probe_ok": probe.returncode == 0,
                "timestamp": self._ts(),
            }
        except Exception as exc:
            logger.exception("cluster health failed")
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }

    def get_metadata(self) -> Dict[str, Any]:
        blocked = self._require_enabled()
        if blocked:
            return blocked
        topic = self.settings.cluster_demo_topic
        try:
            result = self._run(
                [
                    "docker",
                    "exec",
                    self.settings.primary_broker_container,
                    "kafka-topics",
                    "--bootstrap-server",
                    self.settings.cluster_internal_bootstrap,
                    "--describe",
                    "--topic",
                    topic,
                ],
                timeout=5,
            )
            return {
                "topic": topic,
                "brokers": self.broker_containers,
                "bootstrap_servers": self.settings.bootstrap_servers,
                "replication_factor": self.settings.replication_factor,
                "partition_info": (
                    result.stdout if result.returncode == 0 else "Topic not found"
                ),
                "timestamp": self._ts(),
            }
        except Exception as exc:
            logger.exception("cluster metadata failed")
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }

    def get_partition_leadership(self) -> Dict[str, Any]:
        blocked = self._require_enabled()
        if blocked:
            return blocked
        topic = self.settings.cluster_demo_topic
        try:
            result = self._run(
                [
                    "docker",
                    "exec",
                    self.settings.primary_broker_container,
                    "kafka-topics",
                    "--bootstrap-server",
                    self.settings.cluster_internal_bootstrap,
                    "--describe",
                    "--topic",
                    topic,
                ],
                timeout=5,
            )
            lines = result.stdout.strip().split("\n") if result.stdout else []
            return {
                "topic": topic,
                "partition_details": lines,
                "timestamp": self._ts(),
            }
        except Exception as exc:
            logger.exception("partition leadership failed")
            return {"status": "error", "message": str(exc), "timestamp": self._ts()}

    def simulate_failure(self, broker_name: str) -> Dict[str, Any]:
        blocked = self._require_enabled()
        if blocked:
            return blocked
        try:
            self._validate_broker(broker_name)
        except ClusterOpsError as exc:
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }
        try:
            stop_result = self._run(["docker", "stop", broker_name], timeout=10)
            if stop_result.returncode != 0:
                logger.error(
                    "docker stop failed broker=%s stderr=%s",
                    broker_name,
                    stop_result.stderr,
                )
                return {
                    "status": "error",
                    "message": stop_result.stderr or "docker stop failed",
                    "timestamp": self._ts(),
                }
            logger.warning("broker_failure_simulated broker=%s", broker_name)
            return {
                "status": "failure_simulated",
                "broker": broker_name,
                "action": "stopped",
                "message": (
                    f"Broker {broker_name} has been stopped. Cluster will rebalance."
                ),
                "recovery_hint": f"Run: docker start {broker_name}",
                "timestamp": self._ts(),
            }
        except Exception as exc:
            logger.exception("simulate failure failed for %s", broker_name)
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }

    def recover_failure(self, broker_name: str) -> Dict[str, Any]:
        blocked = self._require_enabled()
        if blocked:
            return blocked
        try:
            self._validate_broker(broker_name)
        except ClusterOpsError as exc:
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }
        try:
            restart_result = self._run(["docker", "start", broker_name], timeout=10)
            if restart_result.returncode != 0:
                logger.error(
                    "docker start failed broker=%s stderr=%s",
                    broker_name,
                    restart_result.stderr,
                )
                return {
                    "status": "error",
                    "message": restart_result.stderr or "docker start failed",
                    "timestamp": self._ts(),
                }
            logger.info("broker_recovery_initiated broker=%s", broker_name)
            return {
                "status": "recovery_initiated",
                "broker": broker_name,
                "action": "restarted",
                "message": (
                    f"Broker {broker_name} is restarting. "
                    "Cluster will rebalance partitions."
                ),
                "timestamp": self._ts(),
            }
        except Exception as exc:
            logger.exception("recover failure failed for %s", broker_name)
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }

    def consumer_lag_cli(self) -> Dict[str, Any]:
        """CLI-based lag describe (prefer /metrics or /consumer/lag)."""
        blocked = self._require_enabled()
        if blocked:
            return blocked
        group = self.settings.consumer_group_id
        try:
            result = self._run(
                [
                    "docker",
                    "exec",
                    self.settings.primary_broker_container,
                    "kafka-consumer-groups",
                    "--bootstrap-server",
                    self.settings.cluster_internal_bootstrap,
                    "--group",
                    group,
                    "--describe",
                ],
                timeout=5,
            )
            lines = result.stdout.strip().split("\n") if result.stdout else []
            return {
                "consumer_group": group,
                "lag_info": lines,
                "timestamp": self._ts(),
                "note": "Prefer GET /metrics or GET /consumer/lag for in-app lag.",
            }
        except Exception as exc:
            logger.exception("consumer lag cli failed")
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }

    def trigger_rebalance(self) -> Dict[str, Any]:
        blocked = self._require_enabled()
        if blocked:
            return blocked
        group = self.settings.consumer_group_id
        try:
            result = self._run(
                [
                    "docker",
                    "exec",
                    self.settings.primary_broker_container,
                    "kafka-consumer-groups",
                    "--bootstrap-server",
                    self.settings.cluster_internal_bootstrap,
                    "--group",
                    group,
                    "--reset-offsets",
                    "--to-latest",
                    "--execute",
                    "--all-topics",
                ],
                timeout=10,
            )
            return {
                "status": "rebalancing",
                "consumer_group": group,
                "message": "Consumer group rebalancing initiated",
                "output": result.stdout if result.returncode == 0 else result.stderr,
                "timestamp": self._ts(),
            }
        except Exception as exc:
            logger.exception("rebalance trigger failed")
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": self._ts(),
            }
