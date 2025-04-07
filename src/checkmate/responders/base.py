"""
Base message responder interface.

This module defines the base interfaces that message responders can implement.
"""
from typing import Dict, Any, Protocol, Optional, runtime_checkable


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


@runtime_checkable
class NodeInfoReceiver(Protocol):
    """
    Protocol for responders that want to receive node information updates.
    Responders can implement this interface to be notified when node information
    is updated, either from initial connection or from node info packets.
    """
    
    def update_node_info(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """
        Update information about a node in the mesh network.
        
        Args:
            node_id: The ID of the node
            node_data: Dictionary containing node information, including
                      'user' (Dict with user info) and 'hopsAway' (int) if available
        """
        ...