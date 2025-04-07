"""
Check responder module.

This module contains the CheckResponder class that handles
'?check' messages and generates appropriate responses with hop count and signal information.
"""
import logging
from typing import Dict, Any

from ..packet_utils import (
    is_text_message, get_text, get_channel,
    get_name, id_to_hex, get_rssi, get_snr
)
from ..constants import KEY_HOP_LIMIT, KEY_HOP_START


logger = logging.getLogger(__name__)


class CheckResponder:
    """
    Responder that handles check requests.
    
    This responder checks for messages containing "?check"
    and responds with hop count and signal information.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is a check request.
        
        Args:
            packet: The received packet data
            
        Returns:
            True if this packet is a check request, False otherwise
        """
        # Must be a text message on a non-default channel
        if not is_text_message(packet):
            return False
            
        channel = get_channel(packet)
        if channel == 0:
            return False
            
        # Check for ?check pattern in text - exact match after trimming
        text = get_text(packet)
        return text.strip().lower() == "?check"
    
    def handle(self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str) -> bool:
        """
        Process and respond to a check request.
        
        Args:
            packet: The check request packet
            interface: The interface to use for the response
            users: Dictionary mapping user IDs to names
            location: Location identifier for the response
            
        Returns:
            True if handling was successful, False otherwise
        """
        channel = get_channel(packet)
        rssi = get_rssi(packet)
        
        # Calculate SNR as specified in the requirements
        raw_snr = get_snr(packet)
        snr = raw_snr + 10 * 5
        
        # Calculate hop count
        hop_start = packet.get(KEY_HOP_START, 0)
        hop_limit = packet.get(KEY_HOP_LIMIT, 0)
        hop_count = hop_start - hop_limit if hop_start and hop_limit else 0
        
        name = get_name(packet, users, id_to_hex)
        
        # Create response: "copy from N hops away with XXDb and YYDb SNR"
        # Format with no decimal places
        response = f"copy from {hop_count} hops away with {int(rssi)}Db and {int(snr)}Db SNR"
        
        self.logger.info(
            "Responding to check request",
            extra={
                "userName": name,
                "channel": channel,
                "rssi": rssi,
                "snr": snr,
                "hopCount": hop_count,
                "response": response,
            },
        )
        
        interface.sendText(response, channelIndex=channel)
        return True