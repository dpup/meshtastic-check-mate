"""
Weather responder module.

This module contains the WeatherResponder class that handles
'?weather' messages and fetches/formats weather data from OpenWeatherMap.
"""

import logging
import requests
from typing import Dict, Any, Optional

from ..packet_utils import is_text_message, get_text, get_channel, get_name, id_to_hex
from ..constants import OPENWEATHERMAP_API_URL
from .base import ConfigurableResponder


logger = logging.getLogger(__name__)


class WeatherResponder(ConfigurableResponder):
    """
    Responder that handles weather requests.

    This responder checks for messages containing "?weather"
    and responds with current weather information from OpenWeatherMap API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ):
        """
        Initialize the weather responder.

        Args:
            api_key: Optional API key for OpenWeatherMap
            latitude: Optional latitude for location
            longitude: Optional longitude for location
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude

    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is a weather request.

        Args:
            packet: The received packet data

        Returns:
            True if this packet is a weather request, False otherwise
        """
        # Must be a text message on a non-default channel
        if not is_text_message(packet):
            return False

        channel = get_channel(packet)
        if channel == 0:
            return False

        # Check for ?weather - exact match after trimming
        text = get_text(packet)
        return text.strip().lower() == "?weather"

    def handle(
        self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str
    ) -> bool:
        """
        Process and respond to a weather request.

        Args:
            packet: The weather request packet
            interface: The interface to use for the response
            users: Dictionary mapping user IDs to names
            location: Location identifier for the response

        Returns:
            True if handling was successful, False otherwise
        """
        channel = get_channel(packet)
        name = get_name(packet, users, id_to_hex)

        # Check if we have required configuration
        if not self.api_key:
            response = "Weather service not configured: missing API key"
            self.logger.warning(
                "Weather request rejected: missing API key", extra={"userName": name}
            )
            interface.sendText(response, channelIndex=channel)
            return False

        if not self.latitude or not self.longitude:
            response = "Weather service not configured: missing location"
            self.logger.warning(
                "Weather request rejected: missing location",
                extra={
                    "userName": name,
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                },
            )
            interface.sendText(response, channelIndex=channel)
            return False

        # Fetch weather data
        weather_data = self._fetch_weather()
        if not weather_data:
            response = "Unable to fetch weather data. Try again later."
            self.logger.error("Failed to fetch weather data", extra={"userName": name})
            interface.sendText(response, channelIndex=channel)
            return False

        # Create response with weather data
        response = self._format_weather_response(weather_data)

        self.logger.info(
            "Responding to weather request",
            extra={
                "userName": name,
                "channel": channel,
                "response": response,
                "coordinates": f"{self.latitude},{self.longitude}",
            },
        )

        interface.sendText(response, channelIndex=channel)
        return True

    def _fetch_weather(self) -> Optional[Dict[str, Any]]:
        """
        Fetch weather data from OpenWeatherMap API.

        Returns:
            Dictionary with weather data or None if request fails
        """
        if not self.api_key or not self.latitude or not self.longitude:
            return None

        params = {
            "lat": self.latitude,
            "lon": self.longitude,
            "appid": self.api_key,
            "units": "metric",  # Use metric units (Celsius)
            "exclude": "minutely,hourly",  # Exclude data we don't need
        }

        try:
            response = requests.get(OPENWEATHERMAP_API_URL, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    "Weather API error",
                    extra={
                        "status_code": response.status_code,
                        "response": response.text,
                        "params": params,
                    },
                )
                return None
        except requests.RequestException as ex:
            self.logger.error("Weather API request failed", extra={"error": str(ex)})
            return None

    def _format_weather_response(self, weather_data: Dict[str, Any]) -> str:
        """
        Format weather data into a human-readable response.

        Args:
            weather_data: Dictionary with weather data from OpenWeatherMap OneCall API

        Returns:
            Formatted weather report string
        """
        try:
            # Extract relevant weather information
            current = weather_data.get("current", {})
            weather = current.get("weather", [{}])[0] if current else {}

            # Use weather data's lat/lon to create a location name
            location_name = f"Lat {weather_data.get('lat', 0):.2f}, Lon {weather_data.get('lon', 0):.2f}"

            # Current weather conditions
            temp_kelvin = current.get("temp", 273.15)  # Default to 0°C if missing
            temp_celsius = (
                temp_kelvin - 273.15 if temp_kelvin > 100 else temp_kelvin
            )  # Handle if already in Celsius

            feels_like_kelvin = current.get("feels_like", 273.15)
            feels_like_celsius = (
                feels_like_kelvin - 273.15
                if feels_like_kelvin > 100
                else feels_like_kelvin
            )

            humidity = current.get("humidity", 0)
            description = weather.get("description", "unknown weather")
            wind_speed = current.get("wind_speed", 0)

            # Check for weather alerts
            alerts = weather_data.get("alerts", [])
            alert_msg = ""
            if alerts:
                alert = alerts[0]  # Just mention the first alert
                event = alert.get("event", "weather alert")
                alert_msg = f"\n ⚠️ {event}"

            # Format the response
            return (
                f"Weather for {location_name}: {description.capitalize()}\n"
                f"{temp_celsius:.1f}°C (feels like {feels_like_celsius:.1f}°C)\n"
                f"humidity {humidity}%\n"
                f"wind {wind_speed:.1f}m"
                f"{alert_msg}"
            )
        except Exception as ex:
            self.logger.error("Error formatting weather data", extra={"error": str(ex)})
            return "Error formatting weather data"

    def update_config(
        self,
        api_key: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> None:
        """
        Update the configuration for the weather responder.

        Args:
            api_key: Optional API key for OpenWeatherMap
            latitude: Optional latitude for location
            longitude: Optional longitude for location
        """
        if api_key:
            self.api_key = api_key
        if latitude is not None:
            self.latitude = latitude
        if longitude is not None:
            self.longitude = longitude
