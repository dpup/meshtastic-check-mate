"""
Tests for the help responder module.
"""

import unittest
from unittest.mock import MagicMock, patch

from checkmate.responders.help import HelpResponder, COMMAND_DESCRIPTIONS


class TestHelpResponder(unittest.TestCase):
    """Test cases for HelpResponder."""

    def setUp(self):
        """Set up test environment."""
        self.responder = HelpResponder()

    def test_parse_help_request(self):
        """Test parsing different help request formats."""
        # General help
        is_general, command = self.responder.parse_help_request("?help")
        self.assertTrue(is_general)
        self.assertIsNone(command)

        # Specific command help
        is_general, command = self.responder.parse_help_request("?help status")
        self.assertFalse(is_general)
        self.assertEqual(command, "status")

        # Invalid format
        is_general, command = self.responder.parse_help_request("hello")
        self.assertFalse(is_general)
        self.assertIsNone(command)

    def test_get_available_commands(self):
        """Test getting a list of available commands."""
        result = self.responder.get_available_commands()

        # Check that all commands are listed
        for cmd in COMMAND_DESCRIPTIONS.keys():
            self.assertIn(f"{cmd}", result)

        # Check formatting
        self.assertIn("Available commands:", result)
        self.assertIn("Use ?help [command] for details", result)

    def test_get_command_help(self):
        """Test getting help for a specific command."""
        # Valid command
        result = self.responder.get_command_help("status")
        self.assertIn("?status:", result)
        self.assertIn(COMMAND_DESCRIPTIONS["status"], result)

        # Invalid command
        result = self.responder.get_command_help("invalid")
        self.assertIn("Unknown command: ?invalid", result)

    def test_can_handle(self):
        """Test that responder can handle ?help messages."""
        # Set up test data
        packet_help = {"decoded": {"text": "?help", "channel": 1}}
        packet_help_cmd = {"decoded": {"text": "?help status", "channel": 1}}
        packet_other = {"decoded": {"text": "other message", "channel": 1}}
        packet_default_channel = {"decoded": {"text": "?help", "channel": 0}}

        # Test a basic ?help message
        with patch(
            "checkmate.responders.help.is_text_message", return_value=True
        ), patch("checkmate.responders.help.get_channel", return_value=1), patch(
            "checkmate.responders.help.get_text", return_value="?help"
        ):
            self.assertTrue(self.responder.can_handle(packet_help))

        # Test a ?help command message
        with patch(
            "checkmate.responders.help.is_text_message", return_value=True
        ), patch("checkmate.responders.help.get_channel", return_value=1), patch(
            "checkmate.responders.help.get_text", return_value="?help status"
        ):
            self.assertTrue(self.responder.can_handle(packet_help_cmd))

        # Test a different message
        with patch(
            "checkmate.responders.help.is_text_message", return_value=True
        ), patch("checkmate.responders.help.get_channel", return_value=1), patch(
            "checkmate.responders.help.get_text", return_value="other message"
        ):
            self.assertFalse(self.responder.can_handle(packet_other))

        # Test a message on default channel
        with patch(
            "checkmate.responders.help.is_text_message", return_value=True
        ), patch("checkmate.responders.help.get_channel", return_value=0):
            self.assertFalse(self.responder.can_handle(packet_default_channel))

        # Test a non-text message
        with patch("checkmate.responders.help.is_text_message", return_value=False):
            self.assertFalse(self.responder.can_handle({}))

    def test_handle_general_help(self):
        """Test handling a general help request."""
        packet = {}
        interface = MagicMock()
        users = {"some_id": "User"}

        with patch("checkmate.responders.help.get_channel", return_value=1), patch(
            "checkmate.responders.help.get_name", return_value="Test User"
        ), patch(
            "checkmate.responders.help.get_text", return_value="?help"
        ), patch.object(
            self.responder, "get_available_commands"
        ) as mock_get_commands:

            mock_get_commands.return_value = "Available commands list"
            self.responder.handle(packet, interface, users, "Test Location")

        # Verify the response was sent
        interface.sendText.assert_called_once_with(
            "Available commands list", channelIndex=1
        )

    def test_handle_command_help(self):
        """Test handling a specific command help request."""
        packet = {}
        interface = MagicMock()
        users = {"some_id": "User"}

        with patch("checkmate.responders.help.get_channel", return_value=1), patch(
            "checkmate.responders.help.get_name", return_value="Test User"
        ), patch(
            "checkmate.responders.help.get_text", return_value="?help status"
        ), patch.object(
            self.responder, "get_command_help"
        ) as mock_get_help:

            mock_get_help.return_value = "Status command help"
            self.responder.handle(packet, interface, users, "Test Location")

        # Verify the response was sent
        interface.sendText.assert_called_once_with(
            "Status command help", channelIndex=1
        )
        mock_get_help.assert_called_once_with("status")
