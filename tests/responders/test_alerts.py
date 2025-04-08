"""
Unit tests for the alerts responder.
"""
import unittest
from unittest.mock import MagicMock, patch

from checkmate.responders.alerts import AlertsResponder


class TestAlertsResponder(unittest.TestCase):
    """Test cases for AlertsResponder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.responder = AlertsResponder(api_key="test_key", latitude=35.6895, longitude=139.6917)
        # Override message_delay for tests to avoid waiting
        self.responder.message_delay = 0.001
        self.interface_mock = MagicMock()
        self.users = {"!abc123": "TestUser"}

    def test_can_handle_valid_alerts(self):
        """Test can_handle returns True for valid alerts requests."""
        # Create a packet that should be handled
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "channel": 1
        }

        result = self.responder.can_handle(packet)
        self.assertTrue(result)
        
        # Test with whitespace and mixed case
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "  ?AlErTs  "
            },
            "channel": 1
        }

        result = self.responder.can_handle(packet)
        self.assertTrue(result)

    def test_can_handle_invalid_alerts(self):
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
                "text": "?alerts"
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
                "text": "?alerts now"
            },
            "channel": 1
        }
        self.assertFalse(self.responder.can_handle(packet4))

    def test_missing_api_key(self):
        """Test handling when API key is missing."""
        self.responder.api_key = None
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "from": 0x123456,
            "channel": 2
        }

        with patch('checkmate.responders.alerts.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result is False (failed)
            self.assertFalse(result)
            
            # Verify message sent contains error about missing API key
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            self.assertIn("missing API key", sent_text)

    def test_missing_location(self):
        """Test handling when location is missing."""
        self.responder.latitude = None
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "from": 0x123456,
            "channel": 2
        }

        with patch('checkmate.responders.alerts.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result is False (failed)
            self.assertFalse(result)
            
            # Verify message sent contains error about missing location
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            self.assertIn("missing location", sent_text)

    @patch('requests.get')
    def test_no_active_alerts(self, mock_get):
        """Test behavior when there are no active alerts."""
        # Mock response data with no alerts
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lat": 35.6895,
            "lon": 139.6917,
            "timezone": "Asia/Tokyo",
            "timezone_offset": 32400
        }
        mock_get.return_value = mock_response
        
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "from": 0x123456,
            "channel": 2
        }

        with patch('checkmate.responders.alerts.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result is True (success)
            self.assertTrue(result)
            
            # Verify API was called with correct parameters
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            self.assertEqual(kwargs['params']['lat'], 35.6895)
            self.assertEqual(kwargs['params']['lon'], 139.6917)
            self.assertEqual(kwargs['params']['appid'], "test_key")
            self.assertEqual(kwargs['params']['exclude'], "minutely,hourly,daily,current")
            
            # Verify message sent indicates no active alerts
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            self.assertIn("No active weather alerts", sent_text)

    @patch('requests.get')
    def test_active_alerts(self, mock_get):
        """Test behavior when there are active alerts."""
        # Mock response data with alerts
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lat": 35.6895,
            "lon": 139.6917,
            "timezone": "Asia/Tokyo",
            "timezone_offset": 32400,
            "alerts": [
                {
                    "sender_name": "NWS Tokyo",
                    "event": "Flood Warning",
                    "description": (
                        "Flooding caused by heavy rainfall is expected. "
                        "Take precautions and avoid flood-prone areas."
                    )
                }
            ]
        }
        mock_get.return_value = mock_response
        
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "from": 0x123456,
            "channel": 2
        }

        with patch('checkmate.responders.alerts.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result is True (success)
            self.assertTrue(result)
            
            # We should have header and at least one message for the alert 
            # (combined header and description with continuity indicators)
            self.assertGreaterEqual(self.interface_mock.sendText.call_count, 2)
            
            # Check first message (header)
            first_call_args = self.interface_mock.sendText.call_args_list[0]
            first_message = first_call_args[0][0]
            self.assertIn("Weather Alerts", first_message)
            self.assertIn("1 active alert", first_message)
            
            # Check second message (combined alert header and sender with chunk indicator)
            second_call_args = self.interface_mock.sendText.call_args_list[1]
            second_message = second_call_args[0][0]
            self.assertIn("ALERT 1/1", second_message)
            self.assertIn("Flood Warning", second_message)
            self.assertIn("From: NWS Tokyo", second_message)
            self.assertIn("(1/", second_message)  # Check for chunk indicator
            
            # Check description message with chunk indicator
            if len(self.interface_mock.sendText.call_args_list) > 2:
                third_call_args = self.interface_mock.sendText.call_args_list[2]
                third_message = third_call_args[0][0]
                self.assertIn("Flooding", third_message)
                self.assertIn("(2/", third_message)  # Check for chunk indicator

    @patch('requests.get')
    def test_multiple_alerts(self, mock_get):
        """Test behavior when there are multiple active alerts."""
        # Mock response data with multiple alerts
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lat": 35.6895,
            "lon": 139.6917,
            "timezone": "Asia/Tokyo",
            "timezone_offset": 32400,
            "alerts": [
                {
                    "sender_name": "NWS Tokyo",
                    "event": "Flood Warning",
                    "description": (
                        "Flooding caused by heavy rainfall is expected. "
                        "Take precautions and avoid flood-prone areas."
                    )
                },
                {
                    "sender_name": "Japan Meteorological Agency",
                    "event": "Typhoon Advisory",
                    "description": (
                        "Strong winds and heavy rainfall expected. "
                        "Secure loose items and stay indoors if possible."
                    )
                }
            ]
        }
        mock_get.return_value = mock_response
        
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "from": 0x123456,
            "channel": 2
        }

        with patch('checkmate.responders.alerts.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result is True (success)
            self.assertTrue(result)
            
            # We should have header and multiple alert messages
            self.assertGreaterEqual(self.interface_mock.sendText.call_count, 3)
            
            # Check first message (header)
            first_call_args = self.interface_mock.sendText.call_args_list[0]
            first_message = first_call_args[0][0]
            self.assertIn("Weather Alerts", first_message)
            self.assertIn("2 active alerts", first_message)  # Note the plural
            
            # Check for first alert (combined header and sender with chunk indicator)
            second_call_args = self.interface_mock.sendText.call_args_list[1]
            second_message = second_call_args[0][0]
            self.assertIn("ALERT 1/2", second_message)  # Note the 1/2
            self.assertIn("Flood Warning", second_message)
            self.assertIn("From: NWS Tokyo", second_message)
            self.assertIn("(1/", second_message)  # Check for chunk indicator
            
            # Find index of first message of second alert
            second_alert_index = None
            for i, call in enumerate(self.interface_mock.sendText.call_args_list):
                message = call[0][0]
                if "ALERT 2/2" in message:
                    second_alert_index = i
                    break
                    
            self.assertIsNotNone(second_alert_index, "Second alert not found in messages")
            if second_alert_index:
                # Check second alert message
                second_alert_message = self.interface_mock.sendText.call_args_list[second_alert_index][0][0]
                self.assertIn("ALERT 2/2", second_alert_message)
                self.assertIn("Typhoon Advisory", second_alert_message)
                self.assertIn("From: Japan Meteorological Agency", second_alert_message)
                self.assertIn("(1/", second_alert_message)  # Check for chunk indicator

    @patch('requests.get')
    def test_failed_weather_fetch(self, mock_get):
        """Test failed weather data fetching."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "?alerts"
            },
            "from": 0x123456,
            "channel": 2
        }

        with patch('checkmate.responders.alerts.get_name') as mock_get_name:
            mock_get_name.return_value = "TestUser"
            
            result = self.responder.handle(packet, self.interface_mock, self.users, "Base")
            
            # Verify result is False (failed)
            self.assertFalse(result)
            
            # Verify message sent contains error about unable to fetch
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            self.assertIn("Unable to fetch weather alerts", sent_text)


if __name__ == "__main__":
    unittest.main()