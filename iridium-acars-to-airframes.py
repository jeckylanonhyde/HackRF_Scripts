#!/usr/bin/env python3
"""
iridium-acars-to-airframes.py

Send ACARS JSON output from iridium-toolkit to Airframes.io and optionally other destinations.

Usage:
    $ export PYTHONUNBUFFERED=x
    $ reassembler.py -i zmq: -m acars -a json --station YOUR_STATION_IDENT | iridium-acars-to-airframes.py

For more information, visit https://app.airframes.io/about or contact kevin@airframes.io.
"""

import argparse
import json
import logging
import socket
import sys

# Constants
AIRFRAMES_INGEST_HOST = 'feed.airframes.io'
AIRFRAMES_INGEST_PORT = 5590

# Global dictionary to store socket connections
sockets = {}

# Configure logging
logging.basicConfig(format='%(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)

def create_socket(transport, host, port):
    """Create and return a socket connection for the specified transport."""
    try:
        if transport == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif transport == 'udp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            raise ValueError(f"Unsupported transport: {transport}")
        sock.connect((host, int(port)))
        log.info(f"Connected to {transport}:{host}:{port}")
        return sock
    except Exception as e:
        log.warning(f"Error connecting to {transport}:{host}:{port}: {e}. Will retry later.")
        return None

def send_message(message):
    """Send a message to all configured outputs."""
    global sockets
    for output, sock in list(sockets.items()):
        if sock is None:
            # Reconnect if the socket was previously closed
            transport, host, port = output.split(':')
            sockets[output] = create_socket(transport, host, int(port))
            sock = sockets[output]

        if sock:
            try:
                sock.sendall(f"{message}\n".encode('utf-8'))
                log.info(f"Sent message to {output}")
            except Exception as e:
                log.error(f"Error sending message to {output}: {e}")
                sockets[output] = None  # Mark for reconnection

def configure_outputs(outputs, no_airframes):
    """Initialize socket connections for all specified outputs."""
    global sockets

    if not no_airframes:
        outputs = [f"tcp:{AIRFRAMES_INGEST_HOST}:{AIRFRAMES_INGEST_PORT}"] + outputs

    for output in outputs:
        transport, host, port = output.split(':')
        sockets[output] = create_socket(transport, host, int(port))

    if not any(sockets.values()):
        log.error("No valid outputs configured. Exiting.")
        sys.exit(1)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='iridium-acars-to-airframes.py',
        description='Feed Iridium ACARS to Airframes.io and additional remote destinations',
    )
    parser.add_argument('--station', '-s', help='Override station ident')
    parser.add_argument('--verbose', '-v', help='Enable verbose output', action='store_true')
    parser.add_argument('--debug', '-d', help='Enable debug output', action='store_true')
    parser.add_argument('--output', '-o', help='Additional outputs (format: transport:host:port)', default=[], action='append')
    parser.add_argument('--no-airframes', help='Disable automatic Airframes.io output', action='store_true')
    return parser.parse_args()

def process_line(line, station):
    """Process a single line of input, adding station data if needed."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError as e:
        log.warning(f"Error parsing JSON: {e}")
        return None

    if station:
        message.setdefault('source', {})['station_id'] = station

    return json.dumps(message)

def main():
    args = parse_arguments()

    # Set logging levels
    if args.verbose:
        log.setLevel(logging.INFO)
    if args.debug:
        log.setLevel(logging.DEBUG)

    # Configure outputs
    configure_outputs(args.output, args.no_airframes)

    # Process input lines
    for line in sys.stdin:
        line = line.strip()
        if not line:
            log.warning("Received empty line. Ignoring.")
            continue

        if args.verbose:
            print(line)

        if args.station:
            line = process_line(line, args.station)
            if not line:
                continue

        send_message(line)

if __name__ == '__main__':
    main()