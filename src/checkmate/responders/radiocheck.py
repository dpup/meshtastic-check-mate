"""
Radio check responder module.

This module contains the RadioCheckResponder class that handles
'radio check' and 'mesh check' messages and generates appropriate responses.
"""
import logging
import random
import re
from typing import Dict, Any, List

from ..quality import classify_quality, QualityLevel
from ..packet_utils import (
    is_text_message, get_text, get_channel,
    get_snr, get_rssi, get_name, id_to_hex
)
from ..constants import RADIO_CHECK_PATTERN


# Response templates for different signal quality levels
# Each template can use {name} and {loc} placeholders
EXCELLENT_RESPONSES = [
    "{name}, reading you 5 by 5 from {loc}",
    "Good copy {name}, from {loc}",
    "Ack {name}, got a strong signal from {loc}",
]

GOOD_RESPONSES = [
    "{name}, copy from {loc}",
    "Ack {name} from {loc}",
    "{name}, got you here in {loc}",
]

POOR_RESPONSES = [
    "Copy {name}, weak signal from {loc}",
    "{name}, barely got you from {loc}",
    "Ack {name}, but weak signal from {loc}",
]

# Mapping of quality levels to appropriate response templates
RESPONSES: Dict[QualityLevel, List[str]] = {
    QualityLevel.EXCELLENT: EXCELLENT_RESPONSES,
    QualityLevel.VERY_GOOD: EXCELLENT_RESPONSES,
    QualityLevel.GOOD: GOOD_RESPONSES,
    QualityLevel.FAIR: GOOD_RESPONSES,
    QualityLevel.POOR: POOR_RESPONSES,
    QualityLevel.VERY_POOR: POOR_RESPONSES,
}

# Default response when quality level is unknown
DEFAULT_RESPONSE = "Hola!"

logger = logging.getLogger(__name__)


def get_response(quality_level: QualityLevel, name: str, loc: str) -> str:
    """
    Generate an appropriate radio check response based on signal quality.
    
    Selects a random response template appropriate for the given signal quality
    and formats it with the sender's name and responder's location.
    
    Args:
        quality_level: The signal quality classification
        name: The name of the sender requesting radio check
        loc: The location of this node responding to the check
        
    Returns:
        A formatted response message appropriate for the signal quality
    """
    if not isinstance(quality_level, QualityLevel) or quality_level not in RESPONSES:
        logger.warning(
            "Unknown quality level in radio check response",
            extra={"quality_level": str(quality_level)}
        )
        return DEFAULT_RESPONSE

    response_template = random.choice(RESPONSES[quality_level])
    return response_template.format(name=name, loc=loc)


class RadioCheckResponder:
    """
    Responder that handles radio check requests.
    
    This responder checks for messages containing "radio check" or "mesh check"
    and responds with signal quality information.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is a radio check request.
        
        Args:
            packet: The received packet data
            
        Returns:
            True if this packet is a radio check request, False otherwise
        """
        # Must be a text message on a non-default channel
        if not is_text_message(packet):
            return False
            
        channel = get_channel(packet)
        if channel == 0:
            return False
            
        # Check for radio check pattern in text
        text = get_text(packet)
        return bool(re.search(RADIO_CHECK_PATTERN, text, re.IGNORECASE))
    
    def handle(self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str) -> bool:
        """
        Process and respond to a radio check request.
        
        Args:
            packet: The radio check request packet
            interface: The interface to use for the response
            users: Dictionary mapping user IDs to names
            location: Location identifier for the response
            
        Returns:
            True if handling was successful, False otherwise
        """
        channel = get_channel(packet)
        snr = get_snr(packet)
        rssi = get_rssi(packet)
        name = get_name(packet, users, id_to_hex)

        quality = classify_quality(rssi, snr)
        # Use the local get_response function
        response = get_response(quality.overall, name, location)

        self.logger.info(
            "Acknowledging radio check",
            extra={
                "userName": name,
                "channel": channel,
                "rssi": rssi,
                "snr": snr,
                "quality": str(quality),
                "response": response,
            },
        )

        interface.sendText(response, channelIndex=channel)
        return True