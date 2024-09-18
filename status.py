import platform
from pathlib import Path
from typing import Dict
import json


def getStatusFilePath() -> Path:
    """Determine the appropriate status file path based on the OS."""
    if platform.system() == "Darwin":  # macOS
        base_dir = Path.home() / "Library" / "Application Support" / "check-mate"
    else:  # Linux and others
        base_dir = Path.home() / ".local" / "share" / "check-mate"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "status.json"


STATUS_FILE = getStatusFilePath()


def writeStatus(status: Dict[str, any]):
    """Write the current status to the status file."""
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f)


def readStatus() -> Dict[str, any]:
    """Read the current status from the status file."""
    if not STATUS_FILE.exists():
        return {"status": "unknown"}
    with open(STATUS_FILE, "r") as f:
        return json.load(f)
