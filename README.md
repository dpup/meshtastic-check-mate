# Meshtastic Check Mate

_TCP based bot that monitors Meshtastic channels and responds to various commands._

## Overview

Check-Mate provides a variety of useful services to your Meshtastic mesh network:

- **Radio Checks**: Verify signal quality with other nodes
- **Network Status**: Get visibility into your mesh network topology
- **Weather Information**: Access current weather conditions and alerts
- **Signal Reports**: Detailed signal metrics including RSSI and SNR

The bot connects to a Meshtastic node on your network and responds to commands sent on any channel.

## Requirements

- Python 3.7+
- Meshtastic node connected via WiFi to the same network as the machine running this program.

## Installation

Make sure Python 3.7+ is installed, then clone the repo:

```bash
git clone git@github.com:dpup/meshtastic-check-mate
cd meshtastic-check-mate
```

### Method 1: Using Make (Recommended)

The simplest way to set up the project is using the provided Makefile:

```bash
# Create virtualenv and install dependencies
make setup

# Install the package in development mode
make develop
```

### Method 2: Manual Installation

Alternatively, you can install manually:

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .

# For development, install with extra dev dependencies
pip install -e ".[dev]"
```

## Usage

### Running with Make

```bash
# Start the application
make run HOST=meshtastic.local LOCATION="Base Camp" \
  LATITUDE=40.7128 LONGITUDE=-74.0060 WEATHER_API_KEY=your_api_key_here

# Check status
make status

# Run tests
make test

# Run linting
make lint

# Clean up
make clean
```

### Running Directly

Once installed, you can run Check-Mate directly:

```bash
# As a module
python -m checkmate.main --host meshtastic.local --location 'Base Camp' \
  --latitude 40.7128 --longitude -74.0060 --weather-api-key your_api_key_here

# Or using the installed script
check-mate --host meshtastic.local --location 'Base Camp' \
  --latitude 40.7128 --longitude -74.0060 --weather-api-key your_api_key_here
```

## Available Commands

Check-Mate responds to the following commands on any channel except the default channel (channel 0):

### `radio check` or `mesh check`

Triggers a signal quality report. The bot will respond with a message indicating how well it's receiving your signal.

Example:

```
Outrider (a4bc)  : Radio check
Base camp (ffea) : Copy a4bc, 5.75 SNR from Everest Base Camp
```

Responses are randomized and vary based on signal quality.

### `?net`

Displays visible nodes in your net, grouped by hop distance. Only shows nodes that have been seen in the last 3 hours.

Example:

```
Outrider (a4bc)  : ?net
Base camp (ffea) : Net report! In the last 3hrs:
                   - 0 hops x 3
                   - 1 hop x 5
                   - 2 hops x 2
```

### `?check`

Returns signal information with hop count, signal strength (RSSI), and signal-to-noise ratio (SNR).

Example:

```
Outrider (a4bc)  : ?check
Base camp (ffea) : copy from 2 hops away with -85Db and 58Db SNR
```

### `?weather`

Provides current weather information for the node's location. Requires an OpenWeatherMap API key and location coordinates. The location can be obtained either from command-line arguments or automatically from the node's position data.

Example:

```
Outrider (a4bc)  : ?weather
Base camp (ffea) : Weather for (37° 46.49′ N, 122° 25.17′ W):
                   Broken clouds, 14.7°C (feels like 14.3°C)
                   Humidity 80%, Wind 8.2m

                   ⚠️ Beach Hazards
```

### `?alerts`

Provides detailed information about active weather alerts for the node's location. Requires an OpenWeatherMap API key and location coordinates. Sends multiple messages to avoid exceeding the maximum message size, with each alert broken down into manageable chunks with continuity indicators (n/m).

Example:

```
Outrider (a4bc)  : ?alerts
Base camp (ffea) : Weather Alerts for (37° 46.49′ N, 122° 25.17′ W): 1 active alert
Base camp (ffea) : ALERT 1/1: Small Craft Advisory
From: NWS San Francisco Bay Area (1/5)
Base camp (ffea) : ...SMALL CRAFT ADVISORY REMAINS IN EFFECT FROM 3 PM THIS AFTERNOON TO 9 PM PDT FRIDAY... (2/5)
Base camp (ffea) : * WHAT...Northwest winds 15 to 25 kt with gusts up to 30 kt expected. (3/5)
Base camp (ffea) : * WHERE...Coastal waters from Point Pinos to Point Piedras Blancas. (4/5)
Base camp (ffea) : * WHEN...From 3 PM this afternoon to 9 PM PDT Friday. * IMPACTS...Conditions will be hazardous to small craft. (5/5)
```

Messages are sent with a 2-second delay between them to avoid network saturation.

### `?help`

Displays a help message with available commands and basic usage information.

### `?reminders`

Shows a list of currently configured scheduled messages, including their timing, timezone, and target channels. This command is only available when scheduled messages are configured.

## Scheduled Messages

Check-Mate can send automated messages at scheduled times. This feature is useful for regular announcements, net reminders, or periodic information broadcasts.

### Configuration

Scheduled messages are configured using the `--messages` command line argument or the `SCHEDULED_MESSAGES` environment variable:

```bash
# Using command line argument
make run HOST=meshtastic.local \
  --messages "Monday;18:45;America/Los_Angeles;1;Reminder: practice net starts in 15 minutes"

# Using environment variable
SCHEDULED_MESSAGES="Monday;18:45;America/Los_Angeles;1;Reminder: practice net starts in 15 minutes" \
make run HOST=meshtastic.local

# Multiple messages (separate with triple semicolons, newlines, or multiple --messages flags)
SCHEDULED_MESSAGES="Monday;18:45;America/Los_Angeles;1;Net reminder;;;Tuesday,Thursday;20:00;UTC;2;Weekly check-in time" \
make run HOST=meshtastic.local
```

### Message Format

Each scheduled message follows this format: `Day(s);Time;Timezone;ChannelIndex;Message`

- **Day(s)**: Day of the week when the message should be sent
  - Single day: `Monday`, `Tuesday`, etc.
  - Multiple days: `Monday,Wednesday,Friday` (comma-separated)
  - Supports full names (`Monday`) or abbreviations (`Mon`)
- **Time**: 24-hour format `HH:MM` (e.g., `18:45`, `07:30`)
- **Timezone**: IANA timezone identifier (e.g., `America/Los_Angeles`, `Europe/London`, `UTC`)
- **ChannelIndex**: Numeric channel index (e.g., `0` for primary, `1`, `2`, etc.)
- **Message**: The text content to send

### Multiple Message Delimiters

When specifying multiple messages, you can use any of these delimiters (in order of priority):

1. **Triple semicolons (`;;;`)** - Primary delimiter, works well in environment variables
2. **` --messages ` separator** - Secondary delimiter for command-line usage
3. **Newlines** - Fallback delimiter for multi-line strings

### Examples

```bash
# Weekly net reminder every Monday at 6:45 PM Pacific Time on channel 1
--messages "Monday;18:45;America/Los_Angeles;1;Reminder: GRMS practice net starts in 15 minutes"

# Multiple messages for different events across timezones (using triple semicolons)
--messages "Monday;18:45;America/Los_Angeles;1;West Coast practice net reminder;;;Sunday;19:00;America/New_York;2;East Coast emergency communications check;;;Tuesday;14:30;Europe/London;0;UK afternoon check-in"

# Weekday morning announcement in UTC on primary channel
--messages "Monday,Tuesday,Wednesday,Thursday,Friday;08:00;UTC;0;Good morning! Weather update at noon."

# Multiple days with different timezones on channel 3
--messages "Monday,Wednesday,Friday;09:00;America/Chicago;3;Midwest morning net"

# Using triple semicolons in environment variables (easier for complex configurations)
SCHEDULED_MESSAGES="Monday;18:45;America/Los_Angeles;1;West Coast net;;;Tuesday;19:00;America/New_York;1;East Coast net;;;Sunday;20:00;UTC;2;International check-in"
```

### Scheduling Behavior

- **Timing**: Messages are checked every 30 seconds and sent when the current time matches the scheduled time
- **Precision**: Messages are sent within 30 seconds of the scheduled time
- **Duplicate Prevention**: Each message is sent only once per day, even if the service restarts
- **Daily Reset**: The duplicate prevention resets at midnight each day

### Edge Cases and Considerations

> [!WARNING]
> **Important Notes about Service Restarts:**
> 
> **Missed Messages**: If the service is down during a scheduled time, that message will be skipped for that day
> **Duplicate Messages**: If the service restarts within the same minute as a scheduled message, it may send the message again

**Best Practices:**
- Deploy Check-Mate with automatic restart capabilities (e.g., systemd, Docker restart policies, or ECS)
- Monitor service health to ensure scheduled messages are being sent
- Consider using health check URLs to track service availability
- Test scheduled messages during off-peak hours first

## Command Usage

On any Meshtastic node in your mesh network, send any of the supported commands on a non-default channel (any channel except channel 0).

### Arguments

| Arg               | Env                | Description                                                        |
| ----------------- | ------------------ | ------------------------------------------------------------------ |
| -h                | N/A                | Show help                                                          |
| --host            | HOST               | The IP or hostname of the meshtastic node, e.g. `192.168.5.10`     |
| --location        | LOCATION           | Text description of where your node is, e.g. `SF Mission District` |
| --healthcheck     | HEALTHCHECKURL     | URL to send healthcheck pings to when receiving messages           |
| --status          | N/A                | Print JSON of latest status                                        |
| --status-dir      | STATUS_DIR         | Override where the status file is located (see below)              |
| --latitude        | LATITUDE           | Latitude for location services (e.g. weather)                      |
| --longitude       | LONGITUDE          | Longitude for location services (e.g. weather)                     |
| --weather-api-key | WEATHER_API_KEY    | API key for OpenWeatherMap                                         |
| --messages        | SCHEDULED_MESSAGES | Scheduled messages in format: 'Day(s);Time;Timezone;ChannelIndex;Message' |

## Docker

Check-Mate can be run using Docker and Docker Compose:

```bash
# Build and start with docker-compose
HOST=meshtastic.local LOCATION="Base Camp" \
LATITUDE=40.7128 LONGITUDE=-74.0060 \
WEATHER_API_KEY=your_api_key_here \
docker-compose up -d

# Check status
docker-compose exec check-mate python -m checkmate.main --status
```

### Running on ECS

ECS does not use Docker healthchecks directly and the healthcheck runs as a different user than the `appuser` specified in the Dockerfile. To get around this, set the `STATUS_DIR` environment variable to `/tmp` then add the following healthcheck to the container definition (what follows is a terraform snippet):

```terraform
healthCheck = {
    command     = ["CMD-SHELL", "cd /app && python3 -m checkmate.main --status --status-dir=/tmp"]
    interval    = 60
    timeout     = 10
    retries     = 3
    startPeriod = 60
}
```

(These healthchecks and restarts seem to be pretty important, because the underlying meshtastic client can get in a bad state that doesn't trigger the disconnect pubsub topic.)

## Project Structure

```
check-mate/
├── .github/            # GitHub configuration
│   └── workflows/      # GitHub Actions workflows
├── src/                # Source code
│   └── checkmate/      # Main package
│       ├── __init__.py
│       ├── main.py     # Main entry point
│       ├── status.py   # Status management
│       ├── quality.py  # Signal quality
│       ├── packet_utils.py
│       ├── constants.py
│       └── responders/  # Message responders
│           ├── __init__.py
│           ├── base.py
│           ├── radiocheck.py
│           ├── netstat.py
│           └── ...
├── tests/              # Test code
├── Makefile            # Build and development commands
├── Dockerfile          # Standard container definition
└── ...                 # Other supporting files and configurations
```

## CI/CD Pipeline

The project uses GitHub Actions for Continuous Integration and Deployment:

- **PR Validation**: Each pull request runs tests and linting on multiple Python versions
- **CI/CD Pipeline**: Runs on main branch, performs tests and builds/pushes Docker images tagged as `latest`
- **Publish Docker Image**: Builds and pushes Docker images tagged as `release` when code is pushed to release branch

Docker images are available at: `ghcr.io/meshtastic/check-mate` with tags:

- `latest` - latest development version (from main branch)
- `release` - stable release version (from release branch)

For more details, see [.github/CICD.md](.github/CICD.md)

## Contributing

Improvements and enhancements welcome. If you find issues or spot possible
improvements, please submit a pull-request or file an issue.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting locally with `make test` and `make lint`
5. Submit a pull request
6. CI will automatically run tests and linting on your PR

## How I Use Check-Mate

I’ve set up a geographically distributed mesh. Each location has a Meshtastic node connected to the Internet via WiFi and MQTT. Check-Mate instances monitor each node through AWS ECS and Tailscale.

### 1. Network Architecture:

- Tailscale bridges AWS and physical locations.
- Each location has its own local Meshtastic mesh with multiple nodes.
- A gateway node at each location connects to the internet with a fixed IP and MQTT configuration.
- Tailscale allows ECS to access the gateway node.

### 2. Check-Mate Deployment:

- Two Check-Mate instances run in AWS ECS (Elastic Container Service), each monitoring a different Meshtastic node.
- ECS ensures automatic restarts if an instance becomes unresponsive.
- Container logs are sent to CloudWatch for monitoring and troubleshooting.

### 3. Channel Configuration:

- Several non-default channels are set up for different purposes.
- Both Check-Mate instances monitor these channels.
- MQTT bridges the physical meshes, creating shared private channels (as long as the internet is up).

The ECS deployment ensures Check-Mate instances run continuously with minimal maintenance. Health checks automatically restart containers if they become unresponsive, which can happen with long-running Python MQTT clients.
