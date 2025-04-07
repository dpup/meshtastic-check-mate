"""
Radio check response module for Meshtastic communications.

This module handles generating appropriate responses to radio check requests
based on signal quality, sender name, and responder location.
"""
import random
import logging
from typing import Dict, List, Optional

from .quality import QualityLevel


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