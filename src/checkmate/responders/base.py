"""
Base message responder interface.

This module defines the base interface that all message responders must implement.
"""
from typing import Dict, Any, Protocol


class MessageResponder(Protocol):
    """Protocol defining the interface for pluggable message responders."""
    
    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Determine if this responder can handle the given packet.
        
        Args:
            packet: The received packet data
            
        Returns:
            True if this responder can handle the packet, False otherwise
        """
        ...
        
    def handle(self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str) -> bool:
        """
        Process and respond to the packet.
        
        Args:
            packet: The received packet data
            interface: The interface to use for sending responses
            users: Dictionary mapping user IDs to names
            location: Location string for the responder
            
        Returns:
            True if handling was successful, False otherwise
        """
        ...