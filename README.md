# Meshtastic Check Mate

_TCP based bot that monitors **private** channels and responds to radio checks._

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

Check-Mate responds to the following commands on private channels:

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

Provides detailed information about active weather alerts for the node's location. Requires an OpenWeatherMap API key and location coordinates. Sends multiple messages to avoid exceeding the maximum message size, with each alert broken down into manageable chunks.

Example:

```
Outrider (a4bc)  : ?alerts
Base camp (ffea) : Weather Alerts for (37° 46.49′ N, 122° 25.17′ W): 1 active alert
Base camp (ffea) : ALERT 1/1: Small Craft Advisory
Base camp (ffea) : From: NWS San Francisco Bay Area
Base camp (ffea) : ...SMALL CRAFT ADVISORY REMAINS IN EFFECT FROM 3 PM THIS AFTERNOON TO 9 PM PDT FRIDAY...
Base camp (ffea) : * WHAT...Northwest winds 15 to 25 kt with gusts up to 30 kt expected.
Base camp (ffea) : * WHERE...Coastal waters from Point Pinos to Point Piedras Blancas.
Base camp (ffea) : * WHEN...From 3 PM this afternoon to 9 PM PDT Friday.
Base camp (ffea) : * IMPACTS...Conditions will be hazardous to small craft.
```

## Command Usage

In a private channel on a different node to the one connected to `check-mate`, send any of the supported commands mentioned above.

### Arguments

| Arg              | Env            | Description                                                        |
| ---------------- | -------------- | ------------------------------------------------------------------ |
| -h               | N/A            | Show help                                                          |
| --host           | HOST           | The IP or hostname of the meshtastic node, e.g. `192.168.5.10`     |
| --location       | LOCATION       | Text description of where your node is, e.g. `SF Mission District` |
| --healthcheck    | HEALTHCHECKURL | URL to send healthcheck pings to when receiving messages           |
| --status         | N/A            | Print JSON of latest status                                        |
| --status-dir     | STATUS_DIR     | Override where the status file is located (see below)              |
| --latitude       | LATITUDE       | Latitude for location services (e.g. weather)                      |
| --longitude      | LONGITUDE      | Longitude for location services (e.g. weather)                     |
| --weather-api-key| WEATHER_API_KEY| API key for OpenWeatherMap                                         |

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
