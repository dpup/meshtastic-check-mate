"""
Status responder module.

This module contains the StatusResponder class that handles
'?status' messages and returns the current status and uptime information.
"""
import logging
import time
from typing import Dict, Any

from ..packet_utils import (
    is_text_message, get_text, get_channel,
    get_name, id_to_hex
)
from ..status import StatusManager


class StatusResponder:
    """
    Responder that handles status check requests.
    
    This responder checks for messages containing "?status"
    and responds with uptime and current status information.
    """
    
    def __init__(self, status_manager: StatusManager):
        """
        Initialize the StatusResponder with a reference to StatusManager.
        
        Args:
            status_manager: The StatusManager instance to get status information from
        """
        self.logger = logging.getLogger(__name__)
        self.status_manager = status_manager
        self.packet_count = 0
        self.message_count = 0
    
    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is a status check request.
        
        Args:
            packet: The received packet data
            
        Returns:
            True if this packet is a status check request, False otherwise
        """
        # Must be a text message on a non-default channel
        if not is_text_message(packet):
            return False
            
        channel = get_channel(packet)
        if channel == 0:
            return False
            
        # Check for status pattern in text
        text = get_text(packet)
        return text.strip().lower() == "?status"
    
    def handle(self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str) -> bool:
        """
        Process and respond to a status check request.
        
        Args:
            packet: The status check request packet
            interface: The interface to use for the response
            users: Dictionary mapping user IDs to names
            location: Location identifier for the response
            
        Returns:
            True if handling was successful, False otherwise
        """
        channel = get_channel(packet)
        name = get_name(packet, users, id_to_hex)
        
        # Get status information
        status = self.status_manager.read_status()
            
        # Calculate uptime
        current_time = time.time()
        start_time = status.get("start_time", current_time)
        uptime_seconds = int(current_time - start_time)
        
        # Format uptime
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m"
        
        # Get current status
        current_status = status.get("status", "unknown")
        
        # Get packet counts
        packet_count = status.get("packet_count", 0)
        message_count = status.get("message_count", 0)
        
        # Format response
        response = f"{current_status}. {uptime_str} uptime. {packet_count} packets ({message_count} msgs)"
        
        self.logger.info(
            "Responding to status check",
            extra={
                "userName": name,
                "channel": channel,
                "response": response,
            },
        )
        
        interface.sendText(response, channelIndex=channel)
        return True