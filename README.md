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
make run HOST=meshtastic.local LOCATION="Base Camp"

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
python -m checkmate.main --host meshtastic.local --location 'Base Camp'

# Or using the installed script
check-mate --host meshtastic.local --location 'Base Camp'
```

In a private channel on a different node to the one connected to `check-mate`, send a message containing `radio check` or `mesh check` (case insensitive and spaces are ignored).

### Arguments

| Arg           | Env            | Description                                                        |
| ------------- | -------------- | ------------------------------------------------------------------ |
| -h            | N/A            | Show help                                                          |
| --host        | HOST           | The IP or hostname of the meshtastic node, e.g. `192.168.5.10`     |
| --location    | LOCATION       | Text description of where your node is, e.g. `SF Mission District` |
| --healthcheck | HEALTHCHECKURL | URL to send healthcheck pings to when receiving messages           |
| --status      | N/A            | Print JSON of latest status                                        |
| --status-dir  | STATUS_DIR     | Override where the status file is located (see below)              |

### Example radio check

```
Outrider (a4bc)  : Radio check
Base camp (ffea) : Copy a4bc, 5.75 SNR from Everest Base Camp
```

Responses are randomized, to make it a bit more interesting.

## Docker

Check-Mate can be run using Docker and Docker Compose:

```bash
# Build and start with docker-compose
HOST=meshtastic.local LOCATION="Base Camp" docker-compose up -d

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
│       ├── ci-cd.yml   # CI/CD pipeline for main branch
│       ├── pr-validation.yml # PR checks
│       └── publish-docker-image.yaml # Docker image publishing
├── src/                # Source code
│   └── checkmate/      # Main package
│       ├── __init__.py
│       ├── main.py     # Main entry point
│       ├── status.py   # Status management
│       ├── quality.py  # Signal quality
│       ├── radiocheck.py
│       ├── packet_utils.py
│       └── constants.py
├── tests/              # Test code
├── setup.py            # Package setup
├── requirements.txt    # Dependencies
├── Makefile            # Build commands
├── Dockerfile          # Container definition
└── compose.yaml        # Docker compose config
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