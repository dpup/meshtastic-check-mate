"""
Unit tests for the weather responder.
"""

import unittest
from unittest.mock import MagicMock, patch

from checkmate.responders.weather import WeatherResponder


class TestWeatherResponder(unittest.TestCase):
    """Test cases for WeatherResponder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.responder = WeatherResponder(
            api_key="test_key", latitude=35.6895, longitude=139.6917
        )
        self.interface_mock = MagicMock()
        self.users = {"!abc123": "TestUser"}

    def test_can_handle_valid_weather(self):
        """Test can_handle returns True for valid weather requests."""
        # Create a packet that should be handled
        packet = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather"},
            "channel": 1,
        }

        result = self.responder.can_handle(packet)
        self.assertTrue(result)

        # Test with whitespace and mixed case
        packet = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "  ?WeAtHeR  "},
            "channel": 1,
        }

        result = self.responder.can_handle(packet)
        self.assertTrue(result)

    def test_can_handle_invalid_weather(self):
        """Test can_handle returns False for invalid requests."""
        # Test non-text message
        packet1 = {"decoded": {"portnum": "NODEINFO_APP"}, "channel": 1}
        self.assertFalse(self.responder.can_handle(packet1))

        # Test default channel
        packet2 = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather"},
            "channel": 0,
        }
        self.assertFalse(self.responder.can_handle(packet2))

        # Test wrong text content
        packet3 = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": "just a regular message",
            },
            "channel": 1,
        }
        self.assertFalse(self.responder.can_handle(packet3))

        # Test partial match
        packet4 = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather today"},
            "channel": 1,
        }
        self.assertFalse(self.responder.can_handle(packet4))

    def test_missing_api_key(self):
        """Test handling when API key is missing."""
        self.responder.api_key = None
        packet = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather"},
            "from": 0x123456,
            "channel": 2,
        }

        with patch("checkmate.responders.weather.get_name") as mock_get_name:
            mock_get_name.return_value = "TestUser"

            result = self.responder.handle(
                packet, self.interface_mock, self.users, "Base"
            )

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
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather"},
            "from": 0x123456,
            "channel": 2,
        }

        with patch("checkmate.responders.weather.get_name") as mock_get_name:
            mock_get_name.return_value = "TestUser"

            result = self.responder.handle(
                packet, self.interface_mock, self.users, "Base"
            )

            # Verify result is False (failed)
            self.assertFalse(result)

            # Verify message sent contains error about missing location
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            self.assertIn("missing location", sent_text)

    @patch("requests.get")
    def test_successful_weather_fetch(self, mock_get):
        """Test successful weather data fetching and response."""
        # Mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lat": 35.6895,
            "lon": 139.6917,
            "timezone": "Asia/Tokyo",
            "timezone_offset": 32400,
            "current": {
                "dt": 1684929490,
                "temp": 20.5,
                "feels_like": 19.8,
                "pressure": 1015,
                "humidity": 65,
                "wind_speed": 3.5,
                "wind_deg": 180,
                "weather": [
                    {
                        "id": 803,
                        "main": "Clouds",
                        "description": "scattered clouds",
                        "icon": "04d",
                    }
                ],
            },
        }
        mock_get.return_value = mock_response

        packet = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather"},
            "from": 0x123456,
            "channel": 2,
        }

        with patch("checkmate.responders.weather.get_name") as mock_get_name:
            mock_get_name.return_value = "TestUser"

            result = self.responder.handle(
                packet, self.interface_mock, self.users, "Base"
            )

            # Verify result is True (success)
            self.assertTrue(result)

            # Verify API was called with correct parameters
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            self.assertEqual(kwargs["params"]["lat"], 35.6895)
            self.assertEqual(kwargs["params"]["lon"], 139.6917)
            self.assertEqual(kwargs["params"]["appid"], "test_key")
            self.assertEqual(kwargs["params"]["exclude"], "minutely,hourly")

            # Verify message sent contains weather information
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]

            # Based on the coordinates in the mock response: 35.6895, 139.6917
            expected_coords = "35° 41.37′ N, 139° 41.50′ E"
            self.assertIn(f"Weather @ {expected_coords}", sent_text)
            self.assertIn(":", sent_text)  # Check for colon after location
            self.assertIn(
                "Scattered clouds, 20.5°C", sent_text
            )  # First letter is capitalized
            self.assertIn("feels like 19.8°C", sent_text)
            self.assertIn("Humidity 65%", sent_text)  # Note capitalization
            self.assertIn("Wind 3.5m/s", sent_text)  # Note capitalization

    @patch("requests.get")
    def test_failed_weather_fetch(self, mock_get):
        """Test failed weather data fetching."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        packet = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "?weather"},
            "from": 0x123456,
            "channel": 2,
        }

        with patch("checkmate.responders.weather.get_name") as mock_get_name:
            mock_get_name.return_value = "TestUser"

            result = self.responder.handle(
                packet, self.interface_mock, self.users, "Base"
            )

            # Verify result is False (failed)
            self.assertFalse(result)

            # Verify message sent contains error about unable to fetch
            self.interface_mock.sendText.assert_called_once()
            sent_text = self.interface_mock.sendText.call_args[0][0]
            self.assertIn("Unable to fetch weather data", sent_text)


if __name__ == "__main__":
    unittest.main()
