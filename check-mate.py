import argparse
import logging
import os
import random
import re
import requests
import sys
import time

from pubsub import pub
from pythonjsonlogger import jsonlogger

import meshtastic
import meshtastic.tcp_interface


class CheckMate:
    """Manages connection with meshtastic node, monitoring private channels and responds to radio checks"""

    def __init__(self, host, location=None, healthCheckURL=None):
        self.host = host
        self.location = location
        self.users = {}
        self.iface = None
        self.connected = False
        self.lastHealthCheck = None
        self.healthCheckURL = healthCheckURL
        self.logger = logging.getLogger(__name__)

        pub.subscribe(self.onReceive, "meshtastic.receive")
        pub.subscribe(self.onConnect, "meshtastic.connection.established")
        pub.subscribe(self.onDisconnect, "meshtastic.connection.lost")

    def start(self):
        """Start the connection and listen for incoming messages"""

        while True:
            try:
                self.logger.info("Connecting...", extra={"host": self.host})
                self.connected = True
                self.iface = meshtastic.tcp_interface.TCPInterface(hostname=self.host)
                try:
                    while self.connected:
                        time.sleep(5)
                except KeyboardInterrupt:
                    # On keyboard interrupt, close the connection and exit.
                    self.logger.info("Shutting down...", extra={"host": self.host})
                    self.iface.close()
                    return 0

            except Exception as ex:
                self.logger.error(
                    "Error with connection: %s",
                    ex,
                    extra={"host": self.host, "error": ex},
                )
                self.logger.info("Retrying in 5 seconds...")
                time.sleep(5)

    def onConnect(self, interface, topic=pub.AUTO_TOPIC):
        """called when we (re)connect to the radio"""
        if interface.nodes:
            for node in interface.nodes.values():
                self.updateUser(node["user"])
        self.logger.info("Connected...")

    def onDisconnect(self, interface, topic=pub.AUTO_TOPIC):
        """called when we disconnect from the radio"""
        self.logger.info("Disconnected... waiting for reconnect...")
        self.connected = False

    def onReceive(self, packet, interface):
        """called when a packet arrives"""

        self.reportHealth()

        try:
            if self.isNodeInfo(packet):
                if "user" in packet["decoded"]:
                    self.updateUser(packet["decoded"]["user"])
                else:
                    self.logger.info("Ignoring missing user", extra={"packet": packet})
                return

            if self.isTextMessage(packet):
                channel = self.getChannel(packet)
                text = self.getText(packet)
                name = self.getName(packet, interface)

                if channel == 0:
                    self.logger.info(
                        "Ignoring message to default channel",
                        extra={"name": name, "text": text},
                    )
                    return

                if not re.search(r"(mesh|radio)\s*check", text, re.IGNORECASE):
                    self.logger.info(
                        "Not a radio check",
                        extra={"name": name, "channel": channel, "text": text},
                    )
                    return

                self.ackRadioCheck(packet, interface)
                return

        except Exception as ex:
            self.logger.warning(
                "Error processing packet: %s",
                ex,
                extra={"packet": packet},
            )

    def reportHealth(self):
        if self.healthCheckURL is not None:
            if self.lastHealthCheck is None or time.time() - self.lastHealthCheck > 60:
                self.lastHealthCheck = time.time()
                response = requests.head(self.healthCheckURL)
                if response.status_code == 200:
                    self.logger.info("Healthcheck ❤️")
                else:
                    self.logger.warning(
                        "Healthcheck failed",
                        extra={"statusCode": response.status_code},
                    )

    def ackRadioCheck(self, packet, interface):
        """Respond to a radio check"""
        channel = self.getChannel(packet)
        snr = self.getSNR(packet)
        rssi = self.getRSSI(packet)
        text = self.getText(packet)
        name = self.getName(packet, interface)

        self.logger.info(
            "Acknowledging radio check",
            extra={
                "name": name,
                "channel": channel,
                "rssi": rssi,
                "snr": snr,
                "text": text,
            },
        )

        interface.sendText(self.getMessage(snr, rssi, name), channelIndex=channel)

    def getMessage(self, snr, rssi, name):
        """generate a random message to respond to a radio check"""
        if self.location:
            loc = self.location
            quality = f"({rssi} RSSI, {snr} SNR)"
            messages = [
                f"{name}, read you 5 by 5 from {loc} {quality}",
                f"👋 {name}, got you from {loc} {quality}",
                f"Copy {name}, {snr} SNR & {rssi} RSSI from {loc}",
                f"Hey {name}, message received from {loc} {quality}",
                f"{name}, loud and clear from {loc} {quality}",
                f"{name}, copy your radio check from {loc} {quality}",
                f"{name}, copy from {loc} {quality}",
                f"{name}, copy {snr} SNR & {rssi} RSSI from {loc}",
            ]
        else:
            messages = [
                f"{name}, read you 5 by 5",
                f"Received your message, {name}",
                f"Hey {name}, got your transmission",
                f"{name}, your message is coming through",
                f"Message received, {name}",
                f"Received your message, {name}",
                f"{name}, got your radio check",
                f"Test received, {name}",
                f"{name}, message received",
                f"Got your message, {name}",
            ]
        return random.choice(messages)

    def updateUser(self, user):
        """Update the ID to name mapping"""
        self.users[user["id"]] = user["shortName"]
        self.logger.info(
            "Updating user identity",
            extra={"id": user["id"], "shortName": user["shortName"]},
        )

    def isNodeInfo(self, packet):
        return "decoded" in packet and packet["decoded"]["portnum"] == "NODEINFO_APP"

    def isTextMessage(self, packet):
        return (
            "decoded" in packet and packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP"
        )

    def getText(self, packet):
        return packet["decoded"]["text"]

    def getChannel(self, packet):
        if "channel" not in packet:
            return 0
        return packet["channel"]

    def getSNR(self, packet):
        if "rxSnr" not in packet:
            return 0
        return packet["rxSnr"]

    def getRSSI(self, packet):
        if "rxRssi" not in packet:
            return 0
        return packet["rxRssi"]

    def getName(self, packet, interface):
        if "from" in packet:
            id = self.idToHex(packet["from"])
            if id in self.users:
                return self.users[id]
        return "???"

    def idToHex(self, nodeId):
        return "!" + hex(nodeId)[2:]


# Basd on unit test here: https://github.com/madzak/python-json-logger/blob/5f85723f4693c7289724fdcda84cfc0b62da74d4/tests/test_jsonlogger.py#L87
def getLogFormat():
    supported_keys = [
        "asctime",
        "message",
        "filename",
        "funcName",
        "levelname",
        "lineno",
    ]
    log_format = lambda x: ["%({0:s})s".format(i) for i in x]
    return " ".join(log_format(supported_keys))


if __name__ == "__main__":

    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        getLogFormat(),
        rename_fields={
            "asctime": "time",
            "funcName": "function",
            "levelname": "level",
            "lineno": "line",
        },
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    logHandler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logHandler],
    )

    parser = argparse.ArgumentParser(
        prog="Meshtastic Check Mate",
        description="Monitors private channels and responds to radio checks",
        epilog="Example: python3 check-mate.py --host meshtastic.local --location 'Base Camp' --healthcheck https://uptime.betterstack.com/api/v1/heartbeat/deadbeef",
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
        dest="healthCheckURL",
        required=False,
        help="URL to report healthchecks to (empty HEAD request)",
        default=os.environ.get("HEALTHCHECKURL"),
    )
    args = parser.parse_args()

    if not args.host:
        parser.error(
            "Please provide a host via --host or the $HOST environment variable"
        )

    checkmate = CheckMate(args.host, args.location, args.healthCheckURL)
    sys.exit(checkmate.start())
