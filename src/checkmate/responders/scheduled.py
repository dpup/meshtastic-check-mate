"""
Scheduled message responder for sending messages at specified times.

This responder handles automatic message sending based on configured schedules.
It supports sending messages on specific days and times to designated channels.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum
from zoneinfo import ZoneInfo

from ..packet_utils import is_text_message, get_text, get_channel, get_name, id_to_hex


class WeekDay(Enum):
    """Enumeration for days of the week."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class ScheduledMessage:
    """Data structure representing a scheduled message."""
    days: List[WeekDay]
    time_str: str  # Format: "HH:MM"
    channel_index: int
    message: str
    timezone: str = "UTC"  # Default to UTC if not specified
    hour: int = 0
    minute: int = 0
    
    def __post_init__(self):
        """Parse time string into hour and minute, and validate timezone."""
        try:
            parts = self.time_str.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid time format: {self.time_str}")
            self.hour = int(parts[0])
            self.minute = int(parts[1])
            
            if not (0 <= self.hour <= 23):
                raise ValueError(f"Invalid hour: {self.hour}")
            if not (0 <= self.minute <= 59):
                raise ValueError(f"Invalid minute: {self.minute}")
                
            # Validate timezone
            try:
                ZoneInfo(self.timezone)
            except Exception:
                raise ValueError(f"Invalid timezone: {self.timezone}")
                
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format '{self.time_str}': {e}")
    
    def get_timezone_info(self) -> ZoneInfo:
        """Get ZoneInfo object for this message's timezone."""
        return ZoneInfo(self.timezone)
    
    def format_summary(self) -> str:
        """Format a human-readable summary of this scheduled message."""
        days_str = ", ".join([day.name.capitalize() for day in self.days])
        preview = self.message[:30] + "..." if len(self.message) > 30 else self.message
        return f"{days_str} at {self.time_str} ({self.timezone}) on channel {self.channel_index}: {preview}"


class ScheduledMessageResponder:
    """
    Responder that sends scheduled messages at configured times.
    
    This responder runs background threads to monitor time and send messages
    according to the configured schedule.
    """
    
    def __init__(self, scheduled_messages: List[ScheduledMessage]):
        """
        Initialize the scheduled message responder.
        
        Args:
            scheduled_messages: List of scheduled messages to send
        """
        self.scheduled_messages = scheduled_messages
        self.logger = logging.getLogger(__name__)
        self.interface = None
        self.stop_event = threading.Event()
        self.scheduler_thread = None
        self.sent_today = set()  # Track messages sent today to avoid duplicates
        
    def can_handle(self, packet: Dict[str, Any]) -> bool:
        """
        Check if this responder can handle the ?reminders command.
        
        Args:
            packet: The received packet data
            
        Returns:
            True if this is a ?reminders command, False otherwise
        """
        if not is_text_message(packet):
            return False
            
        text = get_text(packet)
        if not text:
            return False
            
        # Handle ?reminders command
        return text.strip().lower() in ['?reminders', '?reminder']
        
    def handle(self, packet: Dict[str, Any], interface, users: Dict[str, str], location: str) -> bool:
        """
        Handle the ?reminders command to show scheduled messages.
        
        Args:
            packet: The received packet data
            interface: The interface to use for sending responses
            users: Dictionary mapping user IDs to names
            location: Location string for the responder
            
        Returns:
            True if the packet was handled, False otherwise
        """
        if not self.can_handle(packet):
            return False
            
        try:
            channel = get_channel(packet)
            
            if not self.scheduled_messages:
                response = "No scheduled messages configured."
            else:
                response_lines = [f"Scheduled messages ({len(self.scheduled_messages)}):"]
                for i, msg in enumerate(self.scheduled_messages, 1):
                    response_lines.append(f"{i}. {msg.format_summary()}")
                response = "\n".join(response_lines)
            
            self.logger.info(
                "Responding to ?reminders command",
                extra={
                    "channel": channel,
                    "message_count": len(self.scheduled_messages),
                    "requester": get_name(packet, users, id_to_hex)
                }
            )
            
            interface.sendText(text=response, channelIndex=channel)
            return True
            
        except Exception as e:
            self.logger.error(
                "Error handling ?reminders command",
                extra={"error": str(e)}
            )
            return False
        
    def start_scheduler(self, interface) -> None:
        """
        Start the background scheduler thread.
        
        Args:
            interface: The interface to use for sending messages
        """
        if not self.scheduled_messages:
            self.logger.info("No scheduled messages configured")
            return
            
        self.interface = interface
        self.stop_event.clear()
        
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        self.logger.info(
            "Started scheduled message scheduler",
            extra={"message_count": len(self.scheduled_messages)}
        )
        
    def stop_scheduler(self) -> None:
        """Stop the background scheduler thread."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.stop_event.set()
            self.scheduler_thread.join(timeout=5)
            self.logger.info("Stopped scheduled message scheduler")
            
    def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs in background thread."""
        self.logger.info("Scheduler loop started")
        check_count = 0
        
        while not self.stop_event.is_set():
            try:
                # Process each message with its own timezone
                current_utc = datetime.now(ZoneInfo("UTC"))
                check_count += 1
                
                self.logger.info(
                    "Scheduler check",
                    extra={
                        "utc_time": current_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "scheduled_message_count": len(self.scheduled_messages),
                        "check_count": check_count
                    }
                )
            
                for i, scheduled_msg in enumerate(self.scheduled_messages):
                    # Convert current time to message's timezone
                    msg_tz = scheduled_msg.get_timezone_info()
                    current_time = current_utc.astimezone(msg_tz)
                    current_day = WeekDay(current_time.weekday())
                    current_date = current_time.date()
                    
                    # Reset sent_today at midnight in each timezone
                    msg_date_key = f"{msg_tz}_{current_date}"
                    if not hasattr(self, '_last_dates'):
                        self._last_dates = {}
                    
                    if msg_date_key not in self._last_dates or self._last_dates[msg_date_key] != current_date:
                        # Clear sent messages for this timezone date
                        keys_to_remove = [k for k in self.sent_today if k.startswith(f"{current_date}_{i}_")]
                        for key in keys_to_remove:
                            self.sent_today.discard(key)
                        self._last_dates[msg_date_key] = current_date
                        
                        self.logger.debug(
                            "Reset daily message tracking for timezone",
                            extra={
                                "timezone": str(msg_tz),
                                "date": str(current_date),
                                "message_index": i
                            }
                        )
                    
                    # Check if message should be sent today
                    if current_day not in scheduled_msg.days:
                        continue
                        
                    # Create unique key for this message today
                    msg_key = f"{current_date}_{i}_{scheduled_msg.time_str}_{scheduled_msg.channel_index}"
                    
                    # Check if already sent today
                    if msg_key in self.sent_today:
                        continue
                        
                    # Check if it's time to send
                    if (current_time.hour == scheduled_msg.hour
                            and current_time.minute == scheduled_msg.minute):
                        
                        self.logger.info(
                            "Time match for scheduled message",
                            extra={
                                "message_index": i,
                                "scheduled_time": scheduled_msg.time_str,
                                "timezone": scheduled_msg.timezone,
                                "current_time": current_time.strftime("%H:%M"),
                                "channel_index": scheduled_msg.channel_index
                            }
                        )
                        
                        self._send_scheduled_message(scheduled_msg, i)
                        self.sent_today.add(msg_key)
                        
                # Sleep for 30 seconds to avoid excessive CPU usage
                self.stop_event.wait(30)
                
            except Exception as e:
                self.logger.error(
                    "Error in scheduler loop",
                    extra={"error": str(e), "error_type": type(e).__name__}
                )
                # Sleep a bit longer on error to avoid rapid error loops
                self.stop_event.wait(60)
        
        self.logger.info("Scheduler loop stopped")
                
    def _send_scheduled_message(self, scheduled_msg: ScheduledMessage, message_index: int) -> None:
        """
        Send a scheduled message.
        
        Args:
            scheduled_msg: The scheduled message to send
            message_index: Index of the message in the scheduled_messages list
        """
        try:
            if not self.interface:
                self.logger.error(
                    "No interface available for sending message",
                    extra={"message_index": message_index}
                )
                return
                
            self.logger.info(
                "Sending scheduled message",
                extra={
                    "message_index": message_index,
                    "channel_index": scheduled_msg.channel_index,
                    "scheduled_time": scheduled_msg.time_str,
                    "timezone": scheduled_msg.timezone,
                    "message_preview": scheduled_msg.message[:50] + "..." 
                    if len(scheduled_msg.message) > 50 else scheduled_msg.message,
                    "message_length": len(scheduled_msg.message)
                }
            )
            
            # Safety check - never send to invalid channel index
            if scheduled_msg.channel_index < 0:
                self.logger.error(
                    "Cannot send scheduled message - invalid channel index",
                    extra={
                        "message_index": message_index,
                        "channel_index": scheduled_msg.channel_index
                    }
                )
                return
            
            self.interface.sendText(
                text=scheduled_msg.message,
                channelIndex=scheduled_msg.channel_index
            )
            
            self.logger.info(
                "Successfully sent scheduled message",
                extra={
                    "message_index": message_index,
                    "channel_index": scheduled_msg.channel_index
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to send scheduled message",
                extra={
                    "message_index": message_index,
                    "channel_index": scheduled_msg.channel_index,
                    "timezone": scheduled_msg.timezone,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )


def parse_scheduled_messages(messages_arg: str) -> List[ScheduledMessage]:
    """
    Parse scheduled messages from command line argument format.
    
    Expected format: "Day(s);Time;Timezone;ChannelIndex;Message"
    Multiple messages can be separated by:
    1. Triple semicolons (;;;) - Primary delimiter
    2. " --messages " - Secondary delimiter
    3. Newlines - Fallback delimiter
    
    Days can be single day or comma-separated list (e.g., "Monday" or "Monday,Wednesday")
    Timezone is required (e.g., "America/Los_Angeles", "Europe/London", "UTC")
    ChannelIndex is the numeric channel index (e.g., 0, 1, 2)
    
    Args:
        messages_arg: Command line argument containing scheduled messages
        
    Returns:
        List of parsed ScheduledMessage objects
        
    Raises:
        ValueError: If the format is invalid
    """
    if not messages_arg:
        return []
        
    logger = logging.getLogger(__name__)
    messages = []
    
    # Split multiple messages using various delimiters
    # Priority: 1) Triple semicolons (;;;), 2) --messages separator, 3) newlines
    message_strings = []
    
    # First try triple semicolons as primary delimiter
    if ';;;' in messages_arg:
        message_strings = [msg.strip() for msg in messages_arg.split(';;;') if msg.strip()]
        logger.debug(f"Split messages using triple semicolons: found {len(message_strings)} messages")
    else:
        # Fallback to --messages separator
        message_strings = [msg.strip() for msg in messages_arg.split(' --messages ') if msg.strip()]
        if len(message_strings) == 1:
            # Final fallback to newlines
            message_strings = [msg.strip() for msg in messages_arg.split('\n') if msg.strip()]
    
    logger.info(f"Parsing {len(message_strings)} scheduled message(s)")
    
    for msg_str in message_strings:
        try:
            parts = msg_str.split(';')
            if len(parts) != 5:
                raise ValueError(
                    f"Expected 5 parts separated by ';' "
                    f"(Day;Time;Timezone;ChannelIndex;Message), got {len(parts)}: {msg_str}"
                )
            
            # Format: Day(s);Time;Timezone;ChannelIndex;Message
            days_str, time_str, timezone, channel_index_str, message = parts
            
            # Parse days
            day_names = [day.strip().upper() for day in days_str.split(',')]
            days = []
            
            day_mapping = {
                'MONDAY': WeekDay.MONDAY,
                'TUESDAY': WeekDay.TUESDAY, 
                'WEDNESDAY': WeekDay.WEDNESDAY,
                'THURSDAY': WeekDay.THURSDAY,
                'FRIDAY': WeekDay.FRIDAY,
                'SATURDAY': WeekDay.SATURDAY,
                'SUNDAY': WeekDay.SUNDAY,
                'MON': WeekDay.MONDAY,
                'TUE': WeekDay.TUESDAY,
                'WED': WeekDay.WEDNESDAY, 
                'THU': WeekDay.THURSDAY,
                'FRI': WeekDay.FRIDAY,
                'SAT': WeekDay.SATURDAY,
                'SUN': WeekDay.SUNDAY,
            }
            
            for day_name in day_names:
                if day_name not in day_mapping:
                    raise ValueError(f"Invalid day name: {day_name}")
                days.append(day_mapping[day_name])
            
            # Parse channel index
            try:
                channel_index = int(channel_index_str.strip())
                if channel_index < 0:
                    raise ValueError(f"Channel index must be non-negative, got: {channel_index}")
            except ValueError:
                raise ValueError(
                    f"Invalid channel index '{channel_index_str.strip()}': "
                    f"must be a non-negative integer"
                )
            
            # Validate timezone by trying to create ZoneInfo
            try:
                ZoneInfo(timezone.strip())
            except Exception:
                raise ValueError(f"Invalid timezone: {timezone.strip()}")
                
            scheduled_msg = ScheduledMessage(
                days=days,
                time_str=time_str.strip(),
                channel_index=channel_index,
                message=message.strip(),
                timezone=timezone.strip()
            )
            
            messages.append(scheduled_msg)
            
            logger.debug(
                "Parsed scheduled message",
                extra={
                    "days": [d.name for d in days],
                    "time": time_str.strip(),
                    "timezone": timezone.strip(),
                    "channel_index": channel_index,
                    "message_length": len(message.strip())
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing scheduled message '{msg_str}': {e}")
            raise ValueError(f"Error parsing scheduled message '{msg_str}': {e}")
    
    logger.info(f"Successfully parsed {len(messages)} scheduled message(s)")        
    return messages