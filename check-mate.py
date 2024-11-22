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
from meshtastic.protobuf import portnums_pb2

from status import StatusManager, Status
from quality import classifyQuality
from radiocheck import getResponse


"""Max frequency with which to report healthchecks."""
HEALTH_CHECK_THROTTLE = 60

"""Max amount of time since radio traffic was received before we consider process unhealthy."""
UNHEALTHY_TIMEOUT = 5 * 60

"""The amount of silence before we actively try to probe the device."""
PROBE_TIMEOUT = 30


class CheckMate:
    """Manages connection with meshtastic node, monitoring private channels and responds to radio checks"""

    def __init__(self, statusManager, host, location, healthCheckURL):
        self.statusManager = statusManager
        self.host = host
        self.location = location
        self.healthCheckURL = healthCheckURL
        self.lastHealthCheck = None

        self.users = {}
        self.iface = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        self.status = {
            "status": "starting",
            "start_time": time.time(),
        }

        pub.subscribe(self.onReceive, "meshtastic.receive")
        pub.subscribe(self.onConnect, "meshtastic.connection.established")
        pub.subscribe(self.onDisconnect, "meshtastic.connection.lost")

    def start(self):
        """Start the connection and listen for incoming messages"""
        isFirstRun = True
        try:
            while True:
                try:
                    self.logger.info("Connecting...", extra={"host": self.host})
                    self.connected = True
                    self.iface = meshtastic.tcp_interface.TCPInterface(
                        hostname=self.host,
                        noNodes=(not isFirstRun),
                    )
                    isFirstRun = False
                    while self.connected:
                        time.sleep(5)
                        lastUpdate = time.time() - self.status["update_time"]
                        if lastUpdate > PROBE_TIMEOUT:
                            self.sendProbe()
                        if lastUpdate > UNHEALTHY_TIMEOUT:
                            self.setStatus(Status.UNKNOWN)

                except Exception as ex:
                    self.logger.error(
                        "Error with connection: %s",
                        ex,
                        extra={"host": self.host, "error": ex},
                    )
                    self.logger.info("Retrying in 5 seconds...")
                    self.setStatus(Status.RESTARTING)
                    time.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("Shutting down...", extra={"host": self.host})
            self.setStatus(Status.SHUTDOWN)
            return 0

    def sendProbe(self):
        self.logger.info("Sending probe...")
        # TODO: See if this is enough. Might want to actually send a test packet
        # though that could potentially add noise to the network.
        self.setStatus(Status.PROBING)
        self.iface.sendHeartbeat()
        self.setStatus(Status.ACTIVE)
        # self.iface.sendData("probe", portNum=portnums_pb2.PortNum.PRIVATE_APP)

    def setStatus(self, status, ping=False):
        """updates current status"""
        self.status["status"] = status
        self.status["update_time"] = time.time()
        self.status["user_count"] = len(self.users)
        if ping:
            self.status["last_device_ping"] = time.time()
        self.logger.info("Status updated", extra=self.status)
        self.statusManager.writeStatus(self.status)

    def onConnect(self, interface, topic=pub.AUTO_TOPIC):
        """called when we (re)connect to the radio"""
        if interface.nodes:
            for node in interface.nodes.values():
                self.updateUser(node["user"])
        self.logger.info("Connected...")
        self.setStatus(Status.CONNECTED, ping=True)

    def onDisconnect(self, interface, topic=pub.AUTO_TOPIC):
        """called when we disconnect from the radio"""
        self.logger.info("Disconnected... waiting for reconnect...")
        self.connected = False
        self.setStatus(Status.DISCONNECTED)

    def onReceive(self, packet, interface):
        """called when a packet arrives"""

        self.reportHealth()
        self.setStatus(Status.ACTIVE, ping=True)

        # TODO: Turn this back off or demote to DEBUG level.
        extra = packet
        if "decoded" in packet:
            extra = packet["decoded"]
            if "payload" in extra:
                del extra["payload"]
        self.logger.info("Received packet", extra=extra)

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
                        extra={"userName": name, "text": text},
                    )
                    return

                if not re.search(r"(mesh|radio)\s*check", text, re.IGNORECASE):
                    self.logger.info(
                        "Not a radio check",
                        extra={"userName": name, "channel": channel, "text": text},
                    )
                    return

                self.ackRadioCheck(packet, interface)
                return

        except Exception as ex:
            excType, excObj, excTb = sys.exc_info()
            fname = os.path.split(excTb.tb_frame.f_code.co_filename)[1]

            self.logger.warning(
                "Error processing packet: %s",
                ex,
                extra={
                    "excType": excType,
                    "excFilename": fname,
                    "excLine": excTb.tb_lineno,
                    "packet": packet,
                },
            )

    def reportHealth(self):
        if self.healthCheckURL is not None:
            timeSinceLastHealthcheck = time.time() - self.lastHealthCheck
            if (
                self.lastHealthCheck is None
                or timeSinceLastHealthcheck > HEALTH_CHECK_THROTTLE
            ):
                self.lastHealthCheck = time.time()
                response = requests.head(self.healthCheckURL)
                if response.status_code == 200:
                    self.logger.info(
                        "Health check posted",
                        extra={
                            "responseBody": response.text,
                            "responseText": response.headers,
                        },
                    )
                else:
                    self.logger.warning(
                        "Health check failed",
                        extra={"statusCode": response.status_code},
                    )
            else:
                self.logger.info(
                    "Health check skipped",
                    extra={"timeSinceLastHealthcheck": timeSinceLastHealthcheck},
                )

    def ackRadioCheck(self, packet, interface):
        """Respond to a radio check"""
        channel = self.getChannel(packet)
        snr = self.getSNR(packet)
        rssi = self.getRSSI(packet)
        name = self.getName(packet, interface)

        quality = classifyQuality(rssi, snr)
        response = getResponse(quality.overall, name, self.location)

        self.logger.info(
            "Acknowledging radio check",
            extra={
                "userName": name,
                "channel": channel,
                "rssi": rssi,
                "snr": snr,
                "quality": quality,
                "response": response,
            },
        )

        interface.sendText(response, channelIndex=channel)

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


# Based on unit test here: https://github.com/madzak/python-json-logger/blob/5f85723f4693c7289724fdcda84cfc0b62da74d4/tests/test_jsonlogger.py#L87
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
        "--status",
        action="store_true",
        dest="status",
        required=False,
        help="Get status of the current check-mate process",
    )
    parser.add_argument(
        "--status-dir",
        dest="statusDir",
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
        dest="healthCheckURL",
        required=False,
        help="URL to report healthchecks to (empty HEAD request)",
        default=os.environ.get("HEALTHCHECKURL"),
    )
    args = parser.parse_args()

    statusManager = StatusManager(args.statusDir)

    if args.status:
        sys.exit(statusManager.dump())

    if not args.host:
        parser.error(
            "Please provide a host via --host or the $HOST environment variable"
        )

    checkmate = CheckMate(statusManager, args.host, args.location, args.healthCheckURL)
    sys.exit(checkmate.start())
