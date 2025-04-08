"""
Weather alerts responder module.

This module contains the AlertsResponder class that handles
'?alerts' messages and fetches/formats detailed weather alert information.
"""

import logging
import requests
import textwrap
import time
from typing import Dict, Any, Optional, List

from ..packet_utils import is_text_message, get_text, get_channel, get_name, id_to_hex
from ..constants import OPENWEATHERMAP_API_URL
from .base import ConfigurableResponder


logger = logging.getLogger(__name__)


class AlertsResponder(ConfigurableResponder):
    """
    Responder that handles weather alert requests.

    This responder checks for messages containing "?alerts"
    and responds with detailed information about current weather alerts.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ):
        """
        Initialize the alerts responder.

        Args:
            api_key: Optional API key for OpenWeatherMap
            latitude: Optional latitude for location
            longitude: Optional longitude for location
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.max_message_length = 140  # Maximum characters per message
        self.message_delay = 2.0  # Delay between messages in seconds

    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if the packet is an alerts request.

        Args:
            packet: The received packet data

        Returns:
            True if this packet is an alerts request, False otherwise
        """
        # Must be a text message on a non-default channel
        if not is_text_message(packet):
            return False

        channel = get_channel(packet)
        if channel == 0:
            return False

        # Check for ?alerts - exact match after trimming
        text = get_text(packet)
        return text.strip().lower() == "?alerts"

    def handle(
        self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str
    ) -> bool:
        """
        Process and respond to an alerts request.

        Args:
            packet: The alerts request packet
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
            response = "Weather alerts service not configured: missing API key"
            self.logger.warning(
                "Alerts request rejected: missing API key", extra={"userName": name}
            )
            interface.sendText(response, channelIndex=channel)
            return False

        if not self.latitude or not self.longitude:
            response = "Weather alerts service not configured: missing location"
            self.logger.warning(
                "Alerts request rejected: missing location",
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
            response = "Unable to fetch weather alerts. Try again later."
            self.logger.error("Failed to fetch weather data", extra={"userName": name})
            interface.sendText(response, channelIndex=channel)
            return False

        # Extract and format alerts
        alert_messages = self._format_alert_messages(weather_data)

        if not alert_messages:
            response = "No active weather alerts for your location."
            self.logger.info(
                "No active alerts found",
                extra={
                    "userName": name,
                    "channel": channel,
                    "coordinates": f"{self.latitude},{self.longitude}",
                },
            )
            interface.sendText(response, channelIndex=channel)
            return True

        # Send each alert as a separate message with delay between them
        for i, message in enumerate(alert_messages):
            self.logger.info(
                "Sending alert message",
                extra={
                    "userName": name,
                    "channel": channel,
                    "alertText": message,
                    "messageIndex": i + 1,
                    "totalMessages": len(alert_messages),
                },
            )
            interface.sendText(message, channelIndex=channel)

            # Add delay between messages (except after the last one)
            if i < len(alert_messages) - 1:
                self.logger.debug(f"Pausing for {self.message_delay}s between messages")
                time.sleep(self.message_delay)

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
            "exclude": "minutely,hourly,daily,current",  # Only get alerts
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

    def _format_alert_messages(self, weather_data: Dict[str, Any]) -> List[str]:
        """
        Format weather alerts into separate messages, respecting max message length.

        Args:
            weather_data: Dictionary with weather data from OpenWeatherMap OneCall API

        Returns:
            List of formatted alert messages
        """
        try:
            alerts = weather_data.get("alerts", [])
            if not alerts:
                return []

            messages = []

            # Format location display for the header
            lat = weather_data.get("lat", 0)
            lon = weather_data.get("lon", 0)
            lat_deg = int(abs(lat))
            lat_min = (abs(lat) - lat_deg) * 60
            lat_dir = "N" if lat >= 0 else "S"

            lon_deg = int(abs(lon))
            lon_min = (abs(lon) - lon_deg) * 60
            lon_dir = "E" if lon >= 0 else "W"

            location_display = f"({lat_deg}° {lat_min:.2f}′ {lat_dir}, {lon_deg}° {lon_min:.2f}′ {lon_dir})"

            # We'll handle the header as a separate message (no continuity indicator)
            plural = "s" if len(alerts) > 1 else ""
            header = f"Weather Alerts for {location_display}: {len(alerts)} active alert{plural}"
            messages.append(header)

            # Process each alert
            for i, alert in enumerate(alerts, 1):
                sender = alert.get("sender_name", "Weather Service")
                event = alert.get("event", "Unknown Alert")
                description = alert.get("description", "No details available")

                # Time information is available but not used in current implementation
                # Could be extended to show timestamps in a future version
                # alert.get("start", 0)
                # alert.get("end", 0)

                # Combine alert header and sender info
                combined_header = f"ALERT {i}/{len(alerts)}: {event}"
                if sender:
                    combined_header += f"\nFrom: {sender}"

                # Create message chunks for this alert
                alert_chunks = []

                # First chunk is the header
                alert_chunks.append(combined_header)

                # Break description into chunks respecting max_message_length
                if description:
                    # Clean up description - replace newlines with spaces
                    description = description.replace("\n", " ").strip()

                    # Split into chunks - leave more room for " (nn/nn)" suffix
                    # and account for smaller max length
                    chunks = textwrap.wrap(
                        description,
                        width=self.max_message_length - 8,
                        replace_whitespace=False,
                        break_long_words=True,
                    )

                    alert_chunks.extend(chunks)

                # Add chunk indicators and add to messages list
                total_chunks = len(alert_chunks)
                for chunk_num, chunk in enumerate(alert_chunks, 1):
                    chunk_with_indicator = f"{chunk} ({chunk_num}/{total_chunks})"
                    messages.append(chunk_with_indicator)

            return messages
        except Exception as ex:
            self.logger.error("Error formatting alert data", extra={"error": str(ex)})
            return ["Error processing weather alerts."]

    def update_config(
        self,
        api_key: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> None:
        """
        Update the configuration for the alerts responder.

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
