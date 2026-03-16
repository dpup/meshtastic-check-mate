"""
Automatic traceroute scheduler for Meshtastic mesh network exploration.

Periodically selects a distant node and issues a Meshtastic traceroute to it.
Nodes are weighted by hop distance (further = higher weight) multiplied by a
recency factor (more recently seen = higher weight), so the scheduler favours
nodes that are both far away and reachable.  Each node has a per-node cooldown
to avoid repeatedly tracing the same path.
"""

import logging
import math
import random
import threading
import time
from typing import Any, Dict, Optional

from ..constants import KEY_HOPS_AWAY, TRACEROUTE_COOLDOWN_HOURS, TRACEROUTE_MIN_HOPS
from .base import NodeInfoReceiver


class TracerouteScheduler(NodeInfoReceiver):
    """
    Background scheduler that periodically sends traceroutes to distant mesh nodes.

    Implements NodeInfoReceiver so it receives node updates automatically when
    added to the CheckMate responders list.
    """

    def __init__(self, interval_minutes: float = 30.0) -> None:
        """
        Initialise the scheduler.

        Args:
            interval_minutes: How often (in minutes) to attempt a traceroute.
        """
        self.interval_minutes = interval_minutes
        self.logger = logging.getLogger(__name__)

        # node_id -> {"last_seen": float, "hops": int, "last_traceroute": float | None}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        self.interface = None
        self.stop_event = threading.Event()
        self.scheduler_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # MessageResponder protocol (no-op — we only track node info)
    # ------------------------------------------------------------------

    def can_handle(self, packet: Dict[str, Any]) -> bool:
        return False

    def handle(self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str) -> bool:
        return False

    # ------------------------------------------------------------------
    # NodeInfoReceiver protocol
    # ------------------------------------------------------------------

    def update_node_info(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """
        Record or refresh information about a node.

        Args:
            node_id: Hex node identifier (e.g. '!a1b2c3d4')
            node_data: Raw node data dict; may contain 'hopsAway'
        """
        hops = node_data.get(KEY_HOPS_AWAY, 0)
        with self._lock:
            existing = self.nodes.get(node_id, {})
            self.nodes[node_id] = {
                "last_seen": time.time(),
                "hops": hops,
                "last_traceroute": existing.get("last_traceroute"),
            }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_scheduler(self, interface) -> None:
        """
        Start the background traceroute loop.

        Args:
            interface: Active Meshtastic interface used to send traceroutes.
        """
        self.interface = interface
        self.stop_event.clear()
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="traceroute-scheduler"
        )
        self.scheduler_thread.start()
        self.logger.info(
            "Started traceroute scheduler",
            extra={"interval_minutes": self.interval_minutes},
        )

    def stop_scheduler(self) -> None:
        """Stop the background traceroute loop."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.stop_event.set()
            self.scheduler_thread.join(timeout=5)
            self.logger.info("Stopped traceroute scheduler")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scheduler_loop(self) -> None:
        """Main loop: wait, then pick a target and traceroute it."""
        self.logger.info("Traceroute scheduler loop started")
        while not self.stop_event.is_set():
            # Wait for the configured interval (or until stopped)
            self.stop_event.wait(self.interval_minutes * 60)
            if self.stop_event.is_set():
                break

            try:
                target = self._pick_target()
                if target:
                    self._run_traceroute(target)
                else:
                    self.logger.info(
                        "No eligible nodes for traceroute",
                        extra={
                            "total_nodes": len(self.nodes),
                            "min_hops": TRACEROUTE_MIN_HOPS,
                            "cooldown_hours": TRACEROUTE_COOLDOWN_HOURS,
                        },
                    )
            except Exception as exc:
                self.logger.error(
                    "Unexpected error in traceroute scheduler loop",
                    extra={"error": str(exc), "error_type": type(exc).__name__},
                )

        self.logger.info("Traceroute scheduler loop stopped")

    def _pick_target(self) -> Optional[str]:
        """
        Choose a weighted-random traceroute target.

        Eligibility:
        - hops >= TRACEROUTE_MIN_HOPS (2)
        - not tracerouted within the last TRACEROUTE_COOLDOWN_HOURS (6 h)

        Weight:
            hops * exp(-hours_since_last_seen)

        Nodes seen very recently and many hops away get the highest weight.

        Returns:
            The chosen node_id, or None if no eligible candidates exist.
        """
        now = time.time()
        cooldown_secs = TRACEROUTE_COOLDOWN_HOURS * 3600

        with self._lock:
            candidates: list[str] = []
            weights: list[float] = []

            for node_id, info in self.nodes.items():
                if info["hops"] < TRACEROUTE_MIN_HOPS:
                    continue

                last_tr = info.get("last_traceroute")
                if last_tr is not None and (now - last_tr) < cooldown_secs:
                    continue

                hours_since_seen = (now - info["last_seen"]) / 3600
                weight = info["hops"] * math.exp(-hours_since_seen)
                if weight > 0:
                    candidates.append(node_id)
                    weights.append(weight)

        if not candidates:
            return None

        return random.choices(candidates, weights=weights, k=1)[0]

    def _run_traceroute(self, node_id: str) -> None:
        """
        Issue a Meshtastic traceroute to the given node.

        Records the attempt timestamp before sending so that a slow or failed
        traceroute still counts toward the cooldown window.

        Args:
            node_id: Hex node identifier to traceroute.
        """
        if not self.interface:
            self.logger.warning("Traceroute skipped: no interface available")
            return

        with self._lock:
            info = self.nodes.get(node_id)
            if not info:
                return
            hops = info["hops"]
            # Mark attempt before sending to respect cooldown even on failure
            info["last_traceroute"] = time.time()

        # Use the known hop count plus a small buffer so the route has room
        # to travel; honour the Meshtastic maximum of 7.
        hop_limit = min(hops + 2, 7)

        self.logger.info(
            "Sending traceroute",
            extra={"node_id": node_id, "hops": hops, "hop_limit": hop_limit},
        )

        try:
            self.interface.sendTraceRoute(dest=node_id, hopLimit=hop_limit)
            self.logger.info("Traceroute completed", extra={"node_id": node_id})
        except Exception as exc:
            self.logger.warning(
                "Traceroute failed",
                extra={"node_id": node_id, "error": str(exc)},
            )
