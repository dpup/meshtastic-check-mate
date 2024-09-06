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

    python3 check-mate.py --host meshtastic.local --location 'Base Camp'

### Arguments

| Arg           | Description                                                        |
| ------------- | ------------------------------------------------------------------ |
| -h            | Show help                                                          |
| --host        | The IP or hostname of the meshtastic node, e.g. `192.168.5.10`     |
| --location    | Text description of where your node is, e.g. `SF Mission District` |
| --healthcheck | URL to send healthcheck pings to when receiving messages           |

## Example radio check

    Outrider (a4bc)  : Radio check
    Base camp (ffea) : Copy a4bc, 5.75 SNR from Everest Base Camp

Responses are randomized, to make it a bit more interesting.

## Contributing

Improvements and enhancements welcome. If you find issues or spot possible
improvements, please submit a pull-request or file an issue.
