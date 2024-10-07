from enum import Enum
import platform
from pathlib import Path
from typing import Dict
import json


class Status(str, Enum):
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    PROBING = "probing"
    RESTARTING = "restarting"
    SHUTDOWN = "shutdown"


class StatusManager:
    def __init__(self, baseDir=None):
        if baseDir is None or baseDir == "":
            if platform.system() == "Darwin":  # macOS
                self.baseDir = (
                    Path.home() / "Library" / "Application Support" / "check-mate"
                )
            else:  # Linux and others
                self.baseDir = Path.home() / ".local" / "share" / "check-mate"
        else:
            self.baseDir = Path(baseDir)

        self.baseDir.mkdir(parents=True, exist_ok=True)
        self.statusFile = self.baseDir / "status.json"

    def writeStatus(self, status: Dict[str, any]):
        """Write the current status to the status file."""
        with open(self.statusFile, "w") as f:
            json.dump(status, f)

    def readStatus(self) -> Dict[str, any]:
        """Read the current status from the status file."""
        if not self.statusFile.exists():
            return {"status": Status.UNKNOWN}
        with open(self.statusFile, "r") as f:
            return json.load(f)

    def dump(self):
        """Print the status file."""
        status = self.readStatus()
        print(json.dumps(status))
        return 0 if status["status"] == Status.ACTIVE else 1
