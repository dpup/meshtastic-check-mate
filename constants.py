"""
Constants for the check-mate application.
"""
from enum import Enum
from typing import Dict, List

# Application constants
MAX_HEALTH_CHECK_THROTTLE = 60  # Max frequency for healthcheck reporting in seconds
UNHEALTHY_TIMEOUT = 5 * 60  # Time since last traffic before considering unhealthy
PROBE_TIMEOUT = 30  # Time before sending a probe
CONNECTION_RETRY_DELAY = 5  # Seconds to wait before retrying connection

# Regex patterns
RADIO_CHECK_PATTERN = r"(mesh|radio)\s*check"

# Response formats
UNKNOWN_NAME = "???"  # Default name when sender is unknown

# Packet keys
KEY_DECODED = "decoded"
KEY_PORTNUM = "portnum"
KEY_USER = "user"
KEY_FROM = "from"
KEY_ID = "id"
KEY_SHORT_NAME = "shortName"
KEY_CHANNEL = "channel"
KEY_TEXT = "text"
KEY_SNR = "rxSnr"
KEY_RSSI = "rxRssi"
KEY_PAYLOAD = "payload"

# Port numbers as strings
PORT_NODEINFO = "NODEINFO_APP"
PORT_TEXT_MESSAGE = "TEXT_MESSAGE_APP"