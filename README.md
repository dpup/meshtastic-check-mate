# Meshtastic Check Mate

_TCP based bot that monitors **private** channels and responds to radio checks._

## Requirements

- Python3.x
- Meshtastic Python Library
- [Meshtastic](https://meshtastic.org) node connected via WiFi to the same network as the machine running this program. I use a Heltec V3.

## Installation

Make sure python3 is installed, then clone the repo:

    git clone git@github.com:dpup/meshtastic-check-mate
    cd meshtastic-check-mate

Install dependencies:

    pip3 install -r requirements.txt

## Usage

Run check-mate:

    python3 check_mate.py --host meshtastic.local --location 'Base Camp'

Then in a private channel on a different node to the one connected to `check-mate` send a message containing `radio check` or `mesh check` (case insensitive and spaces are ignored).

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

    Outrider (a4bc)  : Radio check
    Base camp (ffea) : Copy a4bc, 5.75 SNR from Everest Base Camp

Responses are randomized, to make it a bit more interesting.

### Running on ECS

ECS does not use Docker healthchecks directly and the healthcheck runs as a different user than the `appuser` specified in the Dockerfile. To get around this, set the `STATUS_DIR` environment variable to `/tmp` then add the following healthcheck to the container definition (what follows is a terraform snippet):

```terraform
healthCheck = {
    command     = ["CMD-SHELL", "cd /app && python3 -m check_mate --status --status-dir=/tmp"]
    interval    = 60
    timeout     = 10
    retries     = 3
    startPeriod = 60
}
```

(These healthchecks and restarts seem to be pretty important, because the underlying meshtastic client can get in a bad state that doesn't trigger the disconnect pubsub topic.)

## Contributing

Improvements and enhancements welcome. If you find issues or spot possible
improvements, please submit a pull-request or file an issue.
