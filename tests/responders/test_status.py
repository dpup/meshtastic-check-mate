"""
Tests for the status responder module.
"""
import time
import unittest
from unittest.mock import MagicMock, patch

from checkmate.responders.status import StatusResponder
from checkmate.status import StatusManager, Status


class TestStatusResponder(unittest.TestCase):
    """Test cases for StatusResponder."""

    def setUp(self):
        """Set up test environment."""
        self.mock_status_manager = MagicMock(spec=StatusManager)
        self.responder = StatusResponder(self.mock_status_manager)
        
        # Mock status data
        self.status_data = {
            "status": Status.ACTIVE,
            "start_time": time.time() - 3600 * 14.5,  # 14.5 hours ago
            "packet_count": 456,
            "message_count": 45
        }
        self.mock_status_manager.read_status.return_value = self.status_data

    def test_can_handle(self):
        """Test that responder can handle ?status messages."""
        # Set up test data
        packet_status = {"decoded": {"text": "?status", "channel": 1}}
        packet_other = {"decoded": {"text": "other message", "channel": 1}}
        packet_default_channel = {"decoded": {"text": "?status", "channel": 0}}
        
        # Test a ?status message
        with patch('checkmate.responders.status.is_text_message', return_value=True), \
             patch('checkmate.responders.status.get_channel', return_value=1), \
             patch('checkmate.responders.status.get_text', return_value="?status"):
            self.assertTrue(self.responder.can_handle(packet_status))
        
        # Test a different message
        with patch('checkmate.responders.status.is_text_message', return_value=True), \
             patch('checkmate.responders.status.get_channel', return_value=1), \
             patch('checkmate.responders.status.get_text', return_value="other message"):
            self.assertFalse(self.responder.can_handle(packet_other))
        
        # Test a message on default channel
        with patch('checkmate.responders.status.is_text_message', return_value=True), \
             patch('checkmate.responders.status.get_channel', return_value=0):
            self.assertFalse(self.responder.can_handle(packet_default_channel))
        
        # Test a non-text message
        with patch('checkmate.responders.status.is_text_message', return_value=False):
            self.assertFalse(self.responder.can_handle({}))

    def test_handle(self):
        """Test handling a status request."""
        packet = {}
        interface = MagicMock()
        users = {"some_id": "User"}
        
        with patch('checkmate.responders.status.get_channel', return_value=1), \
             patch('checkmate.responders.status.get_name', return_value="Test User"):
            self.responder.handle(packet, interface, users, "Test Location")
        
        # Verify the status was read
        self.mock_status_manager.read_status.assert_called_once()
        
        # Verify the response was sent
        interface.sendText.assert_called_once()
        
        # Extract and verify the response format
        args, kwargs = interface.sendText.call_args
        response_text = args[0]
        
        # Check response content
        self.assertIn("ACTIVE", response_text)  # Status.ACTIVE
        self.assertIn("14h 30m", response_text)
        self.assertIn("456 packets", response_text)
        self.assertIn("45 msgs", response_text)
        
        # Check the channel was set correctly
        self.assertEqual(kwargs.get('channelIndex'), 1)