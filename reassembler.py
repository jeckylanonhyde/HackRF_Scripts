#!/usr/bin/env python3
# vim: set ts=4 sw=4 tw=0 et pm=:

import sys
import argparse
import os
import pickle
from os.path import splitext, basename
import fileinput

import iridiumtk.config
import iridiumtk.reassembler

def parse_comma(arg):
    """Parse comma-separated arguments into a list."""
    return arg.split(',')

def setup_parser():
    """Set up argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")
    parser.add_argument("-i", "--input", default=None, help="Input filename")
    parser.add_argument("-o", "--output", default=None, help="Output filename")
    parser.add_argument("-m", "--mode", required=True, help="Processing mode")
    parser.add_argument("-a", "--args", default=[], type=parse_comma, help="Comma-separated additional arguments")
    parser.add_argument("-s", "--stats", action="store_true", help="Enable statistics")
    parser.add_argument("-d", "--debug", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--station", default=None, help="Optional station ID for ACARS")
    parser.add_argument("remainder", nargs='*', help=argparse.SUPPRESS")
    return parser

def configure_output(config):
    """Configure output file or stream."""
    if config.output in (None, "", "="):
        if config.output in ("", "="):
            config.output = f"{config.outbase}.{config.mode}"
        outfile = sys.stdout if config.output is None else open(config.output, "w")
    else:
        outfile = open(config.output, "w")
    config.outfile = outfile

def load_state(config):
    """Load state from a file if specified."""
    if "state" in config.args:
        statefile = f"{config.mode}.state"
        try:
            with open(statefile, "rb") as f:
                config.state = pickle.load(f)
        except (IOError, EOFError):
            config.state = None

def validate_args(config, validargs):
    """Validate additional arguments against valid ones."""
    for arg in config.args:
        if arg not in validargs:
            raise ValueError(f"Unknown -a option: {arg}")

def setup_input(config, zx):
    """Set up input source."""
    if config.input.startswith("zmq:"):
        import zmq
        try:
            topics = zx.topic if isinstance(zx.topic, list) else [zx.topic]
        except AttributeError:
            sys.stderr.write(f"Mode '{config.mode}' does not support streaming.\n")
            sys.exit(1)
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://localhost:4223")
        for topic in topics:
            socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        config.iobj = iter(socket.recv_string, "")
    else:
        config.iobj = fileinput.input(config.input)

def main():
    parser = setup_parser()
    config = parser.parse_args()

    # Setup statistics if enabled
    if config.stats:
        import curses
        curses.setupterm(fd=sys.stderr.fileno())
        eol = (curses.tigetstr("el") + curses.tigetstr("cr")).decode("ascii")

    # Determine input and output filenames
    config.input = config.input or (config.remainder[0] if config.remainder else "/dev/stdin")
    config.outbase, _ = splitext(config.input)
    config.outbase = basename(config.outbase) if config.outbase.startswith("/dev") else config.outbase
    configure_output(config)

    # Load state if specified
    load_state(config)

    # Initialize plugins and modes
    plugins = iridiumtk.reassembler.get_plugins(iridiumtk.reassembler)
    modes = {
        mode[0]: [plugin] + mode[1:]
        for plugin in plugins.values()
        for mode in plugin.modes
    }

    # Debugging and help output
    if config.debug or config.mode == "help":
        cwd = os.getcwd() + "/"
        for mode, info in sorted(modes.items()):
            path = info[0].__spec__.origin
            path = path[len(cwd):] if path.startswith(cwd) else path
            options = f" - Options: {info[2]}" if len(info) > 2 else ""
            print(f"Mode {mode:<10} Class {info[1].__name__:<22} Source {path:<37}{options}")
        sys.exit(0)

    # Validate mode
    if config.mode not in modes:
        sys.exit(f"No plugin found for mode: {config.mode}")

    zx = modes[config.mode][1]()  # Instantiate the mode class
    validargs = modes[config.mode][2] if len(modes[config.mode]) > 2 else ()
    validate_args(config, validargs)

    # Set input source and run the plugin
    setup_input(config, zx)
    try:
        zx.run(config.iobj)
    except BrokenPipeError as e:
        sys.exit(e)
    except KeyboardInterrupt:
        print()

if __name__ == "__main__":
    main()