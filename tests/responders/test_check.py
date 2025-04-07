"""
Unit tests for the check responder.
"""
import unittest
from unittest.mock import MagicMock, patch

from checkmate.responders.check import CheckResponder


class TestCheckResponder(unittest.TestCase):
    """Test cases for CheckResponder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.responder = CheckResponder()
        self.interface_mock = MagicMock()
        self.users = {"!abc123": "TestUser"}

    def test_can_handle_valid_check(self):
        """Test can_handle returns True for valid check requests."""
        # Create a packet that should be handled
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?check"
            },
            "channel": 1
        }

        result = self.responder.can_handle(packet)
        self.assertTrue(result)
        
        # Test with whitespace and mixed case
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "  ?ChEcK  "
            },
            "channel": 1
        }

        result = self.responder.can_handle(packet)
        self.assertTrue(result)

    def test_can_handle_invalid_check(self):
        """Test can_handle returns False for invalid requests."""
        # Test non-text message
        packet1 = {
            "decoded": {
                "portnum": "NODEINFO_APP"
            },
            "channel": 1
        }
        self.assertFalse(self.responder.can_handle(packet1))

        # Test default channel
        packet2 = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?check"
            },
            "channel": 0
        }
        self.assertFalse(self.responder.can_handle(packet2))

        # Test wrong text content
        packet3 = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "just a regular message"
            },
            "channel": 1
        }
        self.assertFalse(self.responder.can_handle(packet3))
        
        # Test partial match
        packet4 = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?check foo"
            },
            "channel": 1
        }
        self.assertFalse(self.responder.can_handle(packet4))
        
        # Test invalid prefix
        packet5 = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "check?"
            },
            "channel": 1
        }
        self.assertFalse(self.responder.can_handle(packet5))

    def test_handle_check_request(self):
        """Test handling a check request generates correct response."""
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?check"
            },
            "from": 0x123456,
            "channel": 2,
            "rxRssi": -85,
            "rxSnr": 8,
            "hopStart": 3,
            "hopLimit": 1
        }

        with patch('checkmate.responders.check.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result
            self.assertTrue(result)
            
            # Verify message sent
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            sent_channel = self.interface_mock.sendText.call_args[1]["channelIndex"]
            
            # Check message content
            self.assertEqual(sent_channel, 2)
            self.assertIn("copy from 2 hops away", sent_text)
            self.assertIn("with -85Db", sent_text)
            self.assertIn("and 58Db SNR", sent_text)  # 8 + 10*5 = 58


if __name__ == "__main__":
    unittest.main()