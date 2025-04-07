"""
Network status responder module.

This module contains the NetstatResponder class that handles
'?net' messages, reporting network status with node counts by hop distance.
"""

import logging
import time
from typing import Dict, Any, DefaultDict
from collections import defaultdict

from ..packet_utils import is_text_message, get_text, get_channel, get_name, id_to_hex
from ..constants import (
    KEY_FROM,
    KEY_HOP_LIMIT,
    KEY_HOPS_AWAY,
    MAX_HOPS,
    NETSTAT_WINDOW_HOURS,
)
from .base import NodeInfoReceiver


class NetstatResponder(NodeInfoReceiver):
    """
    Responder that handles network status requests.

    This responder checks for messages containing "?net" and responds with
    information about the network nodes seen in the last 3 hours, grouped by hop count.
    It also implements NodeInfoReceiver to get updates about node hop distances.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Dictionary to store node activity information
        # Key: node_id, Value: Dict with 'last_seen' timestamp and 'hops' count
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # Activity window in seconds (default: 3 hours)
        self.activity_window = NETSTAT_WINDOW_HOURS * 60 * 60

    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is a network status request.

        Args:
            packet: The received packet data

        Returns:
            True if this packet is a network status request, False otherwise
        """

        # Must be a text message
        if not is_text_message(packet):
            return False

        # Check for ?net pattern in text
        text = get_text(packet)
        return text.strip().lower() == "?net"

    def handle(
        self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str
    ) -> bool:
        """
        Process and respond to a network status request.

        Args:
            packet: The network status request packet
            interface: The interface to use for the response
            users: Dictionary mapping user IDs to names
            location: Location identifier for the response

        Returns:
            True if handling was successful, False otherwise
        """
        channel = get_channel(packet)
        name = get_name(packet, users, id_to_hex)

        # Generate the network status report
        response = self._generate_report()

        self.logger.info(
            "Responding to network status request",
            extra={
                "userName": name,
                "channel": channel,
                "response": response,
            },
        )

        interface.sendText(response, channelIndex=channel)
        return True

    def update_node_info(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """
        Update information about a node in the mesh network.
        Implements the NodeInfoReceiver protocol.

        Args:
            node_id: The ID of the node
            node_data: Dictionary containing node information, including
                      'user' (Dict with user info) and 'hopsAway' (int) if available
        """
        current_time = time.time()

        # Extract the hop count from the node_data if available
        hops = 0  # Default for directly connected nodes
        if KEY_HOPS_AWAY in node_data:
            hops = node_data[KEY_HOPS_AWAY]

        # Update the node information
        self.nodes[node_id] = {"last_seen": current_time, "hops": hops}
        self.logger.debug(
            "Updated node info from database", extra={"node_id": node_id, "hops": hops}
        )

    def _generate_report(self) -> str:
        """
        Generate a network status report based on nodes seen in the activity window.

        Returns:
            A formatted report string showing node counts by hop distance
        """
        current_time = time.time()
        # Filter nodes seen within the activity window
        active_nodes = {
            k: v
            for k, v in self.nodes.items()
            if current_time - v["last_seen"] <= self.activity_window
        }

        # Count nodes by hop distance
        hop_counts: DefaultDict[int, int] = defaultdict(int)
        for node_info in active_nodes.values():
            hop_counts[node_info["hops"]] += 1

        # Generate the report
        if not hop_counts:
            return f"Net report! No active nodes seen in the last {NETSTAT_WINDOW_HOURS}hrs."

        report_parts = [f"Net report! In the last {NETSTAT_WINDOW_HOURS}hrs:"]
        
        for hops in sorted(hop_counts.keys()):
            node_count = hop_counts[hops]
            hop_text = "0 hops" if hops == 0 else f"{hops} hop{'s' if hops > 1 else ''}"
            report_parts.append(
                f" - {hop_text} x {node_count}"
            )

        return "\n".join(report_parts)
