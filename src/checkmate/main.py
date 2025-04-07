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
from typing import Dict, Optional, Any, List

import requests
from pubsub import pub
from pythonjsonlogger import jsonlogger

import meshtastic
import meshtastic.tcp_interface

from .status import StatusManager, Status
from .packet_utils import is_node_info, is_text_message, get_text, get_channel, get_name, id_to_hex
from .constants import (
    MAX_HEALTH_CHECK_THROTTLE, UNHEALTHY_TIMEOUT, PROBE_TIMEOUT,
    CONNECTION_RETRY_DELAY, KEY_DECODED, KEY_USER, KEY_PAYLOAD, KEY_ID, KEY_SHORT_NAME
)
from .responders import MessageResponder, RadioCheckResponder


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
        responders: Optional[List[MessageResponder]] = None
    ) -> None:
        """
        Initialize a new CheckMate instance.
        
        Args:
            status_manager: Manager for persisting status information
            host: Hostname or IP address of the Meshtastic device
            location: Optional location identifier to include in responses
            health_check_url: Optional URL for external health checks
            responders: Optional list of message responders in priority order
        """
        self.status_manager = status_manager
        self.host = host
        self.location = location or "Unknown Location"
        self.health_check_url = health_check_url
        self.last_health_check: Optional[float] = None

        # Initialize default responders if none provided
        self.responders = responders or [RadioCheckResponder()]
        
        self.users: Dict[str, str] = {}
        self.iface = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
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
                    self.logger.info("Retrying in %d seconds...", CONNECTION_RETRY_DELAY)
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
        if hasattr(interface, 'nodes') and interface.nodes:
            for node in interface.nodes.values():
                if "user" in node:
                    self.update_user(node["user"])
        self.logger.info("Connected...")
        self.set_status(Status.CONNECTED, ping=True)

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
                if KEY_USER in packet[KEY_DECODED]:
                    self.update_user(packet[KEY_DECODED][KEY_USER])
                else:
                    self.logger.info("Ignoring missing user", extra={"packet": packet})
                return

            # Try each responder in order until one handles the packet
            for responder in self.responders:
                if responder.can_handle(packet):
                    self.logger.debug(
                        "Handling packet with responder",
                        extra={"responder": responder.__class__.__name__}
                    )
                    responder.handle(packet, interface, self.users, self.location)
                    return

            # Log if no responder handled the packet
            if is_text_message(packet):
                channel = get_channel(packet)
                text = get_text(packet)
                name = get_name(packet, self.users, id_to_hex)
                
                if channel == 0:
                    self.logger.info(
                        "Ignoring message to default channel",
                        extra={"userName": name, "text": text},
                    )
                else:
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
            current_time - self.last_health_check if self.last_health_check is not None else float('inf')
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
                    "Health check request failed", 
                    extra={"error": str(ex)}
                )
        else:
            self.logger.debug(
                "Health check skipped",
                extra={"timeSinceLastHealthcheck": time_since_last_healthcheck},
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

    # Setup default responders
    responders = [RadioCheckResponder()]
    
    # Start the application
    checkmate = CheckMate(
        status_manager, 
        args.host, 
        args.location, 
        args.health_check_url,
        responders=responders
    )
    return checkmate.start()


if __name__ == "__main__":
    sys.exit(main())