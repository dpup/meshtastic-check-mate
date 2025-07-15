"""
Help responder module.

This module contains the HelpResponder class that handles
'?help' messages and provides information about available commands.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple

from ..packet_utils import is_text_message, get_text, get_channel, get_name, id_to_hex


# Dictionary mapping commands to their descriptions
COMMAND_DESCRIPTIONS = {
    "help": "List available commands or get help on a specific command",
    "status": "Show current status, uptime, and packet statistics",
    "check": "Radio check with hop count and signal quality",
    "net": "Show network statistics for connected nodes",
    "weather": "Get current weather for the node's location",
    "alerts": "Get active weather alerts for the node's location",
    "reminders": "Show currently configured scheduled messages",
}


class HelpResponder:
    """
    Responder that handles help requests.

    This responder checks for messages starting with "?help"
    and provides information about available commands.
    """

    def __init__(self):
        """Initialize the HelpResponder."""
        self.logger = logging.getLogger(__name__)
        self.help_pattern = re.compile(r"^\?help(?:\s+(\w+))?$")

    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is a help request.

        Args:
            packet: The received packet data

        Returns:
            True if this packet is a help request, False otherwise
        """
        # Must be a text message on a non-default channel
        if not is_text_message(packet):
            return False

        channel = get_channel(packet)
        if channel == 0:
            return False

        # Check for help pattern in text
        text = get_text(packet)
        return bool(self.help_pattern.match(text.strip()))

    def parse_help_request(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Parse a help request to determine if it's for a specific command.

        Args:
            text: The message text

        Returns:
            A tuple (is_general_help, command_name) where:
            - is_general_help is True if this is a general help request
            - command_name is the name of the command help was requested for, or None
        """
        match = self.help_pattern.match(text.strip())
        if not match:
            return False, None

        command_name = match.group(1)
        return command_name is None, command_name

    def get_available_commands(self) -> str:
        """
        Get a formatted list of available commands.

        Returns:
            A string listing all available commands
        """
        commands = list(COMMAND_DESCRIPTIONS.keys())
        commands.sort()
        command_list = ", ".join(commands)
        return f"Available commands: {command_list}\n\nUse ?help [command] for details."

    def get_command_help(self, command: str) -> str:
        """
        Get help text for a specific command.

        Args:
            command: The command name to get help for

        Returns:
            A string with the command description or an error message
        """
        if command in COMMAND_DESCRIPTIONS:
            return f"?{command}: {COMMAND_DESCRIPTIONS[command]}"
        else:
            return f"Unknown command: ?{command}"

    def handle(
        self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str
    ) -> bool:
        """
        Process and respond to a help request.

        Args:
            packet: The help request packet
            interface: The interface to use for the response
            users: Dictionary mapping user IDs to names
            location: Location identifier for the response

        Returns:
            True if handling was successful, False otherwise
        """
        channel = get_channel(packet)
        name = get_name(packet, users, id_to_hex)
        text = get_text(packet)

        # Parse the help request
        is_general_help, command_name = self.parse_help_request(text)

        # Generate appropriate response
        if is_general_help:
            response = self.get_available_commands()
        else:
            response = self.get_command_help(command_name)

        self.logger.info(
            "Responding to help request",
            extra={
                "userName": name,
                "channel": channel,
                "request": text,
                "response": response,
            },
        )

        interface.sendText(response, channelIndex=channel)
        return True
