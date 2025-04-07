"""
Status management module for the check-mate application.

Handles connection status tracking and persistence, providing a way to save and 
retrieve the current operational state of the check-mate process.
"""
from enum import Enum
import platform
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union


class Status(str, Enum):
    """
    Connection and operational status states.
    
    Represents the various states a check-mate instance can be in during
    its operation lifecycle.
    """
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    PROBING = "probing"
    RESTARTING = "restarting"
    SHUTDOWN = "shutdown"


# Platform-specific paths for status file storage
DEFAULT_STATUS_PATHS = {
    "Darwin": Path.home() / "Library" / "Application Support" / "check-mate",
    "Linux": Path.home() / ".local" / "share" / "check-mate",
    "Windows": Path.home() / "AppData" / "Local" / "check-mate",
}

# Status file name
STATUS_FILENAME = "status.json"

logger = logging.getLogger(__name__)


class StatusManager:
    """
    Manages the persisted status of the check-mate application.
    
    Provides methods to read, write, and display the current application status
    using a platform-appropriate status file location.
    """
    
    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        """
        Initialize a new StatusManager.
        
        Args:
            base_dir: Optional custom directory to store status files.
                      If not provided, uses platform-specific default locations.
        """
        if base_dir is None or (isinstance(base_dir, str) and base_dir == ""):
            system = platform.system()
            self.base_dir = DEFAULT_STATUS_PATHS.get(
                system, Path.home() / ".local" / "share" / "check-mate"
            )
            logger.debug(f"Using default status directory for {system}: {self.base_dir}")
        else:
            self.base_dir = Path(base_dir)
            logger.debug(f"Using custom status directory: {self.base_dir}")

        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.status_file = self.base_dir / STATUS_FILENAME
        except PermissionError as e:
            logger.error(f"Permission error creating status directory: {e}")
            raise
        except Exception as e:
            logger.error(f"Error setting up status directory: {e}")
            raise

    def write_status(self, status: Dict[str, Any]) -> None:
        """
        Write the current status to the status file.
        
        Args:
            status: Dictionary containing the current status information
        
        Raises:
            IOError: If there's an error writing to the status file
        """
        try:
            with open(self.status_file, "w") as f:
                json.dump(status, f)
                logger.debug(f"Status written to {self.status_file}")
        except (IOError, PermissionError) as e:
            logger.error(f"Error writing status file: {e}")
            raise

    def read_status(self) -> Dict[str, Any]:
        """
        Read the current status from the status file.
        
        Returns:
            Dictionary containing the current status information,
            or a default status if the file doesn't exist
            
        Raises:
            json.JSONDecodeError: If the status file contains invalid JSON
        """
        if not self.status_file.exists():
            logger.debug(f"Status file not found at {self.status_file}")
            return {"status": Status.UNKNOWN}
            
        try:
            with open(self.status_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in status file: {e}")
            raise
        except IOError as e:
            logger.error(f"Error reading status file: {e}")
            return {"status": Status.UNKNOWN}

    def dump(self) -> int:
        """
        Print the status file contents and return appropriate exit code.
        
        Returns:
            0 if status is ACTIVE, 1 otherwise (for use as process exit code)
        """
        status = self.read_status()
        print(json.dumps(status))
        return 0 if status.get("status") == Status.ACTIVE else 1
