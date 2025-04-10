"""
Check-Mate: Meshtastic private channel monitor and radio check responder.

This application connects to a Meshtastic device, monitors radio traffic,
and automatically responds to radio check requests with signal quality information.
"""

import argparse
import logging
import os
import sys
import time
import threading
from typing import Dict, Optional, Any, List

import requests
from pubsub import pub
from pythonjsonlogger import jsonlogger

import meshtastic
import meshtastic.tcp_interface

from .status import StatusManager, Status
from .packet_utils import (
    is_node_info,
    is_text_message,
    get_text,
    get_channel,
    get_name,
    id_to_hex,
)
from .constants import (
    MAX_HEALTH_CHECK_THROTTLE,
    UNHEALTHY_TIMEOUT,
    PROBE_TIMEOUT,
    CONNECTION_RETRY_DELAY,
    KEY_DECODED,
    KEY_USER,
    KEY_PAYLOAD,
    KEY_ID,
    KEY_SHORT_NAME,
    KEY_FROM,
    KEY_POSITION,
    KEY_LATITUDE,
    KEY_LONGITUDE,
)
from .responders import (
    MessageResponder,
    RadioCheckResponder,
    NetstatResponder,
    CheckResponder,
    WeatherResponder,
    AlertsResponder,
    StatusResponder,
    HelpResponder,
)
from .responders.base import NodeInfoReceiver, ConfigurableResponder


class CheckMate:
    """
    Manages connection with meshtastic node, monitoring private channels and responds to radio checks.

    This class handles the connection to a Meshtastic device, listens for incoming messages,
    processes radio check requests, and maintains device status information.
    """

    def __init__(
        self,
        status_manager: StatusManager,
        host: str,
        location: Optional[str] = None,
        health_check_url: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        weather_api_key: Optional[str] = None,
        responders: Optional[List[MessageResponder]] = None,
    ) -> None:
        """
        Initialize a new CheckMate instance.

        Args:
            status_manager: Manager for persisting status information
            host: Hostname or IP address of the Meshtastic device
            location: Optional location identifier to include in responses
            health_check_url: Optional URL for external health checks
            latitude: Optional latitude for location services
            longitude: Optional longitude for location services
            weather_api_key: Optional API key for weather services
            responders: Optional list of message responders in priority order
        """
        self.status_manager = status_manager
        self.host = host
        self.location = location or "Unknown Location"
        self.health_check_url = health_check_url
        self.latitude = latitude
        self.longitude = longitude
        self.weather_api_key = weather_api_key
        self.last_health_check: Optional[float] = None

        # Initialize default responders if none provided
        self.responders = responders or [RadioCheckResponder()]

        self.users: Dict[str, str] = {}
        self.iface = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # Track packet and message counts
        self.packet_count = 0
        self.message_count = 0
        
        self.status: Dict[str, Any] = {
            "status": "starting",
            "start_time": time.time(),
            "update_time": time.time(),
        }

        # Set up pubsub subscriptions
        pub.subscribe(self.on_receive, "meshtastic.receive")
        pub.subscribe(self.on_connect, "meshtastic.connection.established")
        pub.subscribe(self.on_disconnect, "meshtastic.connection.lost")

    def start(self) -> int:
        """
        Start the connection and listen for incoming messages.

        Establishes connection to the Meshtastic device and handles the main
        application loop, including connection retries and status monitoring.

        Returns:
            Exit code (0 for normal exit, non-zero for error)
        """
        is_first_run = True
        try:
            while True:
                try:
                    self.logger.info("Connecting...", extra={"host": self.host})
                    self.set_status(Status.CONNECTING)
                    self.connected = True
                    self.iface = meshtastic.tcp_interface.TCPInterface(
                        hostname=self.host,
                        noNodes=(not is_first_run),
                    )
                    is_first_run = False

                    # Main application loop
                    while self.connected:
                        time.sleep(5)
                        last_update = time.time() - self.status["update_time"]
                        if last_update > PROBE_TIMEOUT:
                            self.send_probe()
                        if last_update > UNHEALTHY_TIMEOUT:
                            self.set_status(Status.UNKNOWN)

                except Exception as ex:
                    self.logger.error(
                        "Error with connection: %s",
                        ex,
                        extra={"host": self.host, "error": str(ex)},
                    )
                    self.logger.info(
                        "Retrying in %d seconds...", CONNECTION_RETRY_DELAY
                    )
                    self.set_status(Status.RESTARTING)
                    time.sleep(CONNECTION_RETRY_DELAY)

        except KeyboardInterrupt:
            self.logger.info("Shutting down...", extra={"host": self.host})
            self.set_status(Status.SHUTDOWN)
            return 0

    def send_probe(self) -> None:
        """
        Send a probe to the device to check if it's still responsive.

        Uses a heartbeat message to probe the device without adding
        unnecessary traffic to the mesh network.
        """
        self.logger.info("Sending probe...")
        self.set_status(Status.PROBING)
        self.iface.sendHeartbeat()
        self.set_status(Status.ACTIVE)

    def set_status(self, status: Status, ping: bool = False) -> None:
        """
        Update the current operational status.

        Updates the status information both in memory and persisted to disk.

        Args:
            status: The new status state
            ping: If True, also updates the last_device_ping timestamp
        """
        self.status["status"] = status
        self.status["update_time"] = time.time()
        self.status["user_count"] = len(self.users)
        
        # Copy packet and message counts to status
        self.status["packet_count"] = self.packet_count
        self.status["message_count"] = self.message_count
        
        if ping:
            self.status["last_device_ping"] = time.time()
        self.logger.info("Status updated", extra=self.status)
        self.status_manager.write_status(self.status)

    def on_connect(self, interface, topic=pub.AUTO_TOPIC) -> None:
        """
        Handler called when we (re)connect to the radio.

        Args:
            interface: The interface that established connection
            topic: The pubsub topic (automatically provided)
        """
        if hasattr(interface, "nodes") and interface.nodes:
            for node_id, node in interface.nodes.items():
                # Update the user info
                if "user" in node:
                    self.update_user(node["user"])

                # Dispatch node info to interested responders
                self.dispatch_node_info(node_id, node)

        self.logger.info("Connected...")
        self.set_status(Status.CONNECTED, ping=True)

        # Start a thread to get the position from our connected device
        self._update_position_from_connected_node(interface)

    def on_disconnect(self, interface, topic=pub.AUTO_TOPIC) -> None:
        """
        Handler called when we disconnect from the radio.

        Args:
            interface: The interface that lost connection
            topic: The pubsub topic (automatically provided)
        """
        self.logger.info("Disconnected... waiting for reconnect...")
        self.connected = False
        self.set_status(Status.DISCONNECTED)

    def on_receive(self, packet: Dict[str, Any], interface) -> None:
        """
        Handler called when a packet arrives.

        Processes incoming packets, including node info updates and uses registered
        responders to handle various message types.

        Args:
            packet: The received packet data
            interface: The interface that received the packet
        """
        self.report_health()
        self.set_status(Status.ACTIVE, ping=True)

        # Update packet counter
        self.packet_count += 1

        # Log packet information (with potentially sensitive data removed)
        extra = packet.copy()
        if KEY_DECODED in packet:
            extra = packet[KEY_DECODED].copy()
            if KEY_PAYLOAD in extra:
                del extra[KEY_PAYLOAD]
        self.logger.info("Received packet", extra=extra)

        try:
            # Process node information updates
            if is_node_info(packet):
                node_id = None
                if KEY_FROM in packet:
                    node_id = id_to_hex(packet[KEY_FROM])

                # Update user info if available
                if KEY_USER in packet[KEY_DECODED]:
                    self.update_user(packet[KEY_DECODED][KEY_USER])
                else:
                    self.logger.info("Ignoring missing user", extra={"packet": packet})

                # Dispatch node info to interested responders
                if node_id and KEY_DECODED in packet:
                    self.dispatch_node_info(node_id, packet[KEY_DECODED])

                return

            # Check if this is a text message and update counter if so
            is_text = is_text_message(packet)
            if is_text:
                self.message_count += 1
            
            # Try each responder in order until one handles the packet
            for responder in self.responders:
                if responder.can_handle(packet):
                    self.logger.debug(
                        "Handling packet with responder",
                        extra={"responder": responder.__class__.__name__},
                    )
                    responder.handle(packet, interface, self.users, self.location)
                    return

            # Log if no responder handled the packet
            if is_text:
                channel = get_channel(packet)
                text = get_text(packet)
                name = get_name(packet, self.users, id_to_hex)

                self.logger.info(
                    "No responder handled message",
                    extra={"userName": name, "channel": channel, "text": text},
                )

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

            self.logger.warning(
                "Error processing packet: %s",
                ex,
                extra={
                    "excType": str(exc_type),
                    "excFilename": fname,
                    "excLine": exc_tb.tb_lineno,
                    "error": str(ex),
                },
            )

    def report_health(self) -> None:
        """
        Report health status to an external monitoring service.

        Sends a HEAD request to the configured health check URL if one is provided.
        Throttles requests to avoid excessive traffic.
        """
        if not self.health_check_url:
            return

        current_time = time.time()
        time_since_last_healthcheck = (
            current_time - self.last_health_check
            if self.last_health_check is not None
            else float("inf")
        )

        if time_since_last_healthcheck > MAX_HEALTH_CHECK_THROTTLE:
            # Update timestamp before making the request to prevent rapid retries on failure
            self.last_health_check = current_time

            try:
                response = requests.head(self.health_check_url, timeout=10)
                if response.status_code == 200:
                    self.logger.info(
                        "Health check posted",
                        extra={
                            "responseStatus": response.status_code,
                            "responseHeaders": str(response.headers),
                        },
                    )
                else:
                    self.logger.warning(
                        "Health check failed",
                        extra={"statusCode": response.status_code},
                    )
            except requests.RequestException as ex:
                self.logger.error(
                    "Health check request failed", extra={"error": str(ex)}
                )
        else:
            self.logger.debug(
                "Health check skipped",
                extra={"timeSinceLastHealthcheck": time_since_last_healthcheck},
            )

    def dispatch_node_info(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """
        Dispatch node information updates to responders that implement NodeInfoReceiver.

        Args:
            node_id: The ID of the node
            node_data: Dictionary containing node information
        """
        for responder in self.responders:
            if isinstance(responder, NodeInfoReceiver):
                try:
                    responder.update_node_info(node_id, node_data)
                except Exception as ex:
                    self.logger.warning(
                        "Error dispatching node info to responder",
                        extra={
                            "responder": responder.__class__.__name__,
                            "node_id": node_id,
                            "error": str(ex),
                        },
                    )

    def update_user(self, user: Dict[str, Any]) -> None:
        """
        Update the ID to name mapping for a user.

        Args:
            user: User information dictionary containing id and shortName
        """
        if KEY_ID in user and KEY_SHORT_NAME in user:
            self.users[user[KEY_ID]] = user[KEY_SHORT_NAME]
            self.logger.info(
                "Updating user identity",
                extra={"id": user[KEY_ID], "shortName": user[KEY_SHORT_NAME]},
            )

    def _update_position_from_connected_node(self, interface) -> None:
        """
        Get position information from the directly connected node.

        This method runs in a separate thread to avoid blocking the main thread
        while waiting for a GPS position to be available.

        Args:
            interface: The interface connected to the Meshtastic device
        """

        def _get_position():
            if self.latitude is not None and self.longitude is not None:
                # Skip if we already have coordinates from command line
                self.logger.info(
                    "Skipping position update: already set via command line",
                    extra={"latitude": self.latitude, "longitude": self.longitude},
                )
                return

            try:
                # Try to get the most accurate position from the connected node
                self.logger.info("Waiting for position from connected node...")
                interface.waitForPosition()

            except Exception as ex:
                self.logger.error(
                    "Error getting position from connected node",
                    extra={"error": str(ex)},
                )

            # Try to get our node info even if the above errored.
            my_node_info = interface.getMyNodeInfo()

            if (
                my_node_info
                and KEY_POSITION in my_node_info
                and KEY_LATITUDE in my_node_info[KEY_POSITION]
                and KEY_LONGITUDE in my_node_info[KEY_POSITION]
            ):

                lat_i = my_node_info[KEY_POSITION][KEY_LATITUDE]
                lon_i = my_node_info[KEY_POSITION][KEY_LONGITUDE]

                if lat_i != 0 and lon_i != 0:  # Check if valid coordinates
                    # Convert from int to float: multiply by 1e-7
                    self.latitude = lat_i * 1e-7
                    self.longitude = lon_i * 1e-7
                    self.logger.info(
                        "Updated position from connected node",
                        extra={
                            "latitude": self.latitude,
                            "longitude": self.longitude,
                        },
                    )

                    # Update any configurable responders with the new coordinates
                    for responder in self.responders:
                        if isinstance(responder, ConfigurableResponder):
                            responder.update_config(
                                latitude=self.latitude, longitude=self.longitude
                            )
            else:
                self.logger.warning(
                    "No position data available from connected node",
                    extra={"my_node_info": str(my_node_info)},
                )

        # Start a separate thread to wait for position without blocking
        position_thread = threading.Thread(target=_get_position)
        position_thread.daemon = True  # Make thread exit when main thread exits
        position_thread.start()


def get_log_format() -> str:
    """
    Create a format string for the JSON logger.

    Returns:
        Format string for structuring log messages
    """
    supported_keys = [
        "asctime",
        "message",
        "filename",
        "funcName",
        "levelname",
        "lineno",
    ]

    def format_keys(x):
        return ["%({0:s})s".format(i) for i in x]

    return " ".join(format_keys(supported_keys))


def main() -> int:
    """
    Main entry point for the check-mate application.

    Parses command line arguments, sets up logging, and starts the application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Set up logging
    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        get_log_format(),
        rename_fields={
            "asctime": "time",
            "funcName": "function",
            "levelname": "level",
            "lineno": "line",
        },
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    log_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[log_handler],
    )

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="check-mate",
        description="Monitors private channels and responds to radio checks",
        epilog="Example: check-mate --host meshtastic.local --location 'Base Camp' "
        "--healthcheck https://uptime.betterstack.com/api/v1/heartbeat/abcdef",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        dest="status",
        required=False,
        help="Get status of the current check-mate process",
    )
    parser.add_argument(
        "--status-dir",
        dest="status_dir",
        required=False,
        help="Override default location of the status dir",
        default=os.environ.get("STATUS_DIR"),
    )
    parser.add_argument(
        "--host",
        dest="host",
        required=False,
        help="IP or hostname for Meshtastic device",
        default=os.environ.get("HOST"),
    )
    parser.add_argument(
        "-l",
        "--location",
        dest="location",
        required=False,
        help="Location to report in radio checks",
        default=os.environ.get("LOCATION"),
    )
    parser.add_argument(
        "--healthcheck",
        dest="health_check_url",
        required=False,
        help="URL to report healthchecks to (empty HEAD request)",
        default=os.environ.get("HEALTHCHECKURL"),
    )
    parser.add_argument(
        "--latitude",
        dest="latitude",
        type=float,
        required=False,
        help="Latitude for location services (e.g. weather)",
        default=os.environ.get("LATITUDE"),
    )
    parser.add_argument(
        "--longitude",
        dest="longitude",
        type=float,
        required=False,
        help="Longitude for location services (e.g. weather)",
        default=os.environ.get("LONGITUDE"),
    )
    parser.add_argument(
        "--weather-api-key",
        dest="weather_api_key",
        required=False,
        help="API key for OpenWeatherMap",
        default=os.environ.get("WEATHER_API_KEY"),
    )
    args = parser.parse_args()

    # Initialize the status manager
    status_manager = StatusManager(args.status_dir)

    # Handle status check request
    if args.status:
        return status_manager.dump()

    # Ensure required parameters are provided
    if not args.host:
        parser.error(
            "Please provide a host via --host or the $HOST environment variable"
        )

    # Setup default responders in priority order
    weather_responder = WeatherResponder(
        args.weather_api_key, args.latitude, args.longitude
    )
    alerts_responder = AlertsResponder(
        args.weather_api_key, args.latitude, args.longitude
    )
    responders = [
        HelpResponder(),     # Help should have highest priority
        RadioCheckResponder(),
        CheckResponder(),
        StatusResponder(status_manager),
        weather_responder,
        alerts_responder,
        NetstatResponder(),  # Also acts as NodeInfoReceiver for hop counts
    ]

    # Start the application
    checkmate = CheckMate(
        status_manager,
        args.host,
        args.location,
        args.health_check_url,
        args.latitude,
        args.longitude,
        args.weather_api_key,
        responders=responders,
    )
    return checkmate.start()


if __name__ == "__main__":
    sys.exit(main())
