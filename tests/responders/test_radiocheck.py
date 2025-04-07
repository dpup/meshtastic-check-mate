"""Tests for the RadioCheckResponder and response generation."""

import unittest
import re
from unittest.mock import patch, MagicMock

from checkmate.responders.radiocheck import RadioCheckResponder, get_response
from checkmate.quality import QualityLevel


class TestRadioCheckResponder(unittest.TestCase):
    """Test case for the RadioCheckResponder class."""

    def setUp(self):
        """Set up test fixtures for RadioCheckResponder tests."""
        self.responder = RadioCheckResponder()
        
    @patch('checkmate.responders.radiocheck.is_text_message')
    def test_can_handle_not_text_message(self, mock_is_text_message):
        """Test can_handle returns False for non-text messages."""
        mock_is_text_message.return_value = False
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertFalse(result)
        mock_is_text_message.assert_called_once_with(packet)
        
    @patch('checkmate.responders.radiocheck.is_text_message')
    @patch('checkmate.responders.radiocheck.get_channel')
    def test_can_handle_default_channel(self, mock_get_channel, mock_is_text_message):
        """Test can_handle returns False for messages on default channel."""
        mock_is_text_message.return_value = True
        mock_get_channel.return_value = 0
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertFalse(result)
        mock_is_text_message.assert_called_once_with(packet)
        mock_get_channel.assert_called_once_with(packet)
        
    @patch('checkmate.responders.radiocheck.is_text_message')
    @patch('checkmate.responders.radiocheck.get_channel')
    @patch('checkmate.responders.radiocheck.get_text')
    @patch('checkmate.responders.radiocheck.re.search')
    def test_can_handle_not_radio_check(self, mock_search, mock_get_text, 
                                       mock_get_channel, mock_is_text_message):
        """Test can_handle returns False for non-radio check messages."""
        mock_is_text_message.return_value = True
        mock_get_channel.return_value = 1
        mock_get_text.return_value = "Hello world"
        mock_search.return_value = None
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertFalse(result)
        mock_is_text_message.assert_called_once_with(packet)
        mock_get_channel.assert_called_once_with(packet)
        mock_get_text.assert_called_once_with(packet)
        mock_search.assert_called_once()
        
    @patch('checkmate.responders.radiocheck.is_text_message')
    @patch('checkmate.responders.radiocheck.get_channel')
    @patch('checkmate.responders.radiocheck.get_text')
    @patch('checkmate.responders.radiocheck.re.search')
    def test_can_handle_radio_check(self, mock_search, mock_get_text, 
                                  mock_get_channel, mock_is_text_message):
        """Test can_handle returns True for radio check messages."""
        mock_is_text_message.return_value = True
        mock_get_channel.return_value = 1
        mock_get_text.return_value = "radio check"
        mock_search.return_value = MagicMock()  # Non-None result
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertTrue(result)
        mock_is_text_message.assert_called_once_with(packet)
        mock_get_channel.assert_called_once_with(packet)
        mock_get_text.assert_called_once_with(packet)
        mock_search.assert_called_once()
        
    @patch('checkmate.responders.radiocheck.get_channel')
    @patch('checkmate.responders.radiocheck.get_snr')
    @patch('checkmate.responders.radiocheck.get_rssi')
    @patch('checkmate.responders.radiocheck.get_name')
    @patch('checkmate.responders.radiocheck.classify_quality')
    @patch('checkmate.responders.radiocheck.get_response')
    def test_handle(self, mock_get_response, mock_classify_quality, mock_get_name,
                   mock_get_rssi, mock_get_snr, mock_get_channel):
        """Test handle processes radio check and sends response."""
        # Setup mocks
        mock_get_channel.return_value = 1
        mock_get_snr.return_value = 10
        mock_get_rssi.return_value = -80
        mock_get_name.return_value = "Test User"
        
        quality = MagicMock()
        quality.overall = QualityLevel.EXCELLENT
        mock_classify_quality.return_value = quality
        
        mock_get_response.return_value = "Test response"
        
        # Test objects
        packet = {}
        interface = MagicMock()
        users = {"user1": "Test User"}
        location = "Test Location"
        
        # Call the method
        result = self.responder.handle(packet, interface, users, location)
        
        # Verify results
        self.assertTrue(result)
        mock_get_channel.assert_called_once_with(packet)
        mock_get_snr.assert_called_once_with(packet)
        mock_get_rssi.assert_called_once_with(packet)
        mock_get_name.assert_called_once()
        mock_classify_quality.assert_called_once_with(-80, 10)
        mock_get_response.assert_called_once_with(QualityLevel.EXCELLENT, "Test User", "Test Location")
        interface.sendText.assert_called_once_with("Test response", channelIndex=1)


class TestResponseGeneration(unittest.TestCase):
    """Test case for the radiocheck module's response text generation."""
    
    def test_excellent_quality(self):
        """Test response for excellent quality."""
        result = get_response(QualityLevel.EXCELLENT, "Alice", "London")
        self.assertIn(
            result,
            [
                "Alice, reading you 5 by 5 from London",
                "Good copy Alice, from London",
                "Ack Alice, got a strong signal from London",
            ],
        )

    def test_very_good_quality(self):
        """Test response for very good quality."""
        result = get_response(QualityLevel.VERY_GOOD, "Bob", "New York")
        self.assertIn(
            result,
            [
                "Bob, reading you 5 by 5 from New York",
                "Good copy Bob, from New York",
                "Ack Bob, got a strong signal from New York",
            ],
        )

    def test_good_quality(self):
        """Test response for good quality."""
        result = get_response(QualityLevel.GOOD, "Charlie", "Paris")
        self.assertIn(
            result,
            [
                "Charlie, copy from Paris",
                "Ack Charlie from Paris",
                "Charlie, got you here in Paris",
            ],
        )

    def test_fair_quality(self):
        """Test response for fair quality."""
        result = get_response(QualityLevel.FAIR, "Dave", "Tokyo")
        self.assertIn(
            result,
            [
                "Dave, copy from Tokyo",
                "Ack Dave from Tokyo",
                "Dave, got you here in Tokyo",
            ],
        )

    def test_poor_quality(self):
        """Test response for poor quality."""
        result = get_response(QualityLevel.POOR, "Eve", "Sydney")
        self.assertIn(
            result,
            [
                "Copy Eve, weak signal from Sydney",
                "Eve, barely got you from Sydney",
                "Ack Eve, but weak signal from Sydney",
            ],
        )

    def test_very_poor_quality(self):
        """Test response for very poor quality."""
        result = get_response(QualityLevel.VERY_POOR, "Frank", "Berlin")
        self.assertIn(
            result,
            [
                "Copy Frank, weak signal from Berlin",
                "Frank, barely got you from Berlin",
                "Ack Frank, but weak signal from Berlin",
            ],
        )

    def test_unknown_quality(self):
        """Test response for unknown quality level."""
        result = get_response("UNKNOWN", "Unknown", "Unknown")
        self.assertEqual(result, "Hola!")


if __name__ == "__main__":
    unittest.main()