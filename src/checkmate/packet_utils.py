"""
Packet processing utilities for Meshtastic communications.

This module provides helper functions for extracting and processing data from
Meshtastic packet objects.
"""
import logging
from typing import Dict, Any, Optional, Union

from .constants import (
    KEY_DECODED, KEY_PORTNUM, KEY_USER, KEY_FROM, KEY_ID, 
    KEY_SHORT_NAME, KEY_CHANNEL, KEY_TEXT, KEY_SNR, KEY_RSSI,
    PORT_NODEINFO, PORT_TEXT_MESSAGE, UNKNOWN_NAME
)

logger = logging.getLogger(__name__)


def is_node_info(packet: Dict[str, Any]) -> bool:
    """
    Check if the packet is a node info packet.
    
    Args:
        packet: The packet to check
        
    Returns:
        True if the packet is a node info packet, False otherwise
    """
    return (
        KEY_DECODED in packet and 
        packet[KEY_DECODED].get(KEY_PORTNUM) == PORT_NODEINFO
    )


def is_text_message(packet: Dict[str, Any]) -> bool:
    """
    Check if the packet is a text message.
    
    Args:
        packet: The packet to check
        
    Returns:
        True if the packet is a text message, False otherwise
    """
    return (
        KEY_DECODED in packet and 
        packet[KEY_DECODED].get(KEY_PORTNUM) == PORT_TEXT_MESSAGE
    )


def get_text(packet: Dict[str, Any]) -> str:
    """
    Extract the text message from a packet.
    
    Args:
        packet: The packet to extract text from
        
    Returns:
        The text message from the packet, or empty string if not present
    """
    if KEY_DECODED not in packet:
        return ""
    return packet[KEY_DECODED].get(KEY_TEXT, "")


def get_channel(packet: Dict[str, Any]) -> int:
    """
    Get the channel index from a packet.
    
    Args:
        packet: The packet to extract channel from
        
    Returns:
        The channel index, or 0 if not present
    """
    return packet.get(KEY_CHANNEL, 0)


def get_snr(packet: Dict[str, Any]) -> float:
    """
    Get the SNR (Signal-to-Noise Ratio) from a packet.
    
    Args:
        packet: The packet to extract SNR from
        
    Returns:
        The SNR value, or 0 if not present
    """
    return float(packet.get(KEY_SNR, 0))


def get_rssi(packet: Dict[str, Any]) -> float:
    """
    Get the RSSI (Received Signal Strength Indicator) from a packet.
    
    Args:
        packet: The packet to extract RSSI from
        
    Returns:
        The RSSI value, or 0 if not present
    """
    return float(packet.get(KEY_RSSI, 0))


def get_name(packet: Dict[str, Any], users: Dict[str, str], id_to_hex) -> str:
    """
    Get the sender's name from a packet.
    
    Args:
        packet: The packet to extract name from
        users: Dictionary mapping user IDs to names
        id_to_hex: Function to convert node ID to hex format
        
    Returns:
        The sender's name, or UNKNOWN_NAME if not found
    """
    if KEY_FROM in packet:
        node_id = id_to_hex(packet[KEY_FROM])
        if node_id in users:
            return users[node_id]
    return UNKNOWN_NAME


def id_to_hex(node_id: int) -> str:
    """
    Convert a node ID to hex format.
    
    Args:
        node_id: The node ID to convert
        
    Returns:
        The node ID in hex format with '!' prefix
    """
    return "!" + hex(node_id)[2:]


def extract_user_info(packet: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Extract user information from a node info packet.
    
    Args:
        packet: The node info packet
        
    Returns:
        Dictionary with user ID and name, or None if not present
    """
    if not is_node_info(packet) or KEY_DECODED not in packet:
        return None
        
    decoded = packet[KEY_DECODED]
    if KEY_USER not in decoded:
        return None
        
    user = decoded[KEY_USER]
    if KEY_ID not in user or KEY_SHORT_NAME not in user:
        return None
        
    return {
        "id": user[KEY_ID],
        "name": user[KEY_SHORT_NAME]
    }