#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A modular and streamlined script for processing Iridium satellite data with improved readability and maintainability.

import os
import sys
import re
import json
import time
import datetime
import argparse
from threading import Thread, Event
from collections import defaultdict

import bitsparser

# --- Argument Parsing ---
def parse_comma(arg):
    return arg.split(',')

def parse_filter(arg):
    """Parse filter options into a structured dictionary."""
    linefilter = {'type': arg, 'attr': None, 'check': None}
    if ',' in linefilter['type']:
        linefilter['type'], linefilter['check'] = linefilter['type'].split(',', 2)
    if '+' in linefilter['type']:
        linefilter['type'], linefilter['attr'] = linefilter['type'].split('+')
    return linefilter

class NegateAction(argparse.Action):
    """Custom action for enabling/disabling stats."""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, option_string[2:4] != 'no')

# Argument Parser Configuration
parser = argparse.ArgumentParser(
    description="Iridium Satellite Data Processor",
    formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
)

# Filters and Processing Options
filters = parser.add_argument_group("Filters")
filters.add_argument("-g", "--good", action="store_const", const=90, dest="min_confidence", help="Drop if confidence < 90")
filters.add_argument("--confidence", type=int, metavar="MIN", help="Set minimum confidence level")
filters.add_argument("-p", "--perfect", action="store_true", help="Drop lines parsed with error correction")
filters.add_argument("-e", "--errorfree", action="store_true", help="Drop unparsable lines")
filters.add_argument("--filter", type=parse_filter, metavar="FILTER", default="All", help="Filter output by type/attribute")

# Output and Format Options
parser.add_argument("-o", "--output", choices=["json", "line", "plot", "zmq"], default="line", help="Output mode")
parser.add_argument("--errorfile", metavar="FILE", help="File for unparsable lines")
parser.add_argument("--stats", "--no-stats", action=NegateAction, dest="do_stats", nargs=0, help="Enable incremental stats")
parser.add_argument("files", nargs="*", help="Input files")

# Parse Arguments
args = parser.parse_args()

# --- Global Settings ---
stats = defaultdict(int)
stats["start"] = time.time()
selected = []
output_mode = args.output

# --- Utility Functions ---
def log(message):
    """Simple logger."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr)

def preprocess_line(line):
    """Preprocess a single line using bitsparser."""
    message = bitsparser.Message(line.strip())
    if args.min_confidence and message.confidence < args.min_confidence:
        return None
    if args.perfect and (message.error or getattr(message, "fixederrs", 0) > 0):
        return None
    return message.upgrade()

def output_line(message):
    """Handle output formatting for a single message."""
    if output_mode == "json":
        print(json.dumps(message.__dict__))
    elif output_mode == "line":
        print(message.pretty())
    elif output_mode == "zmq":
        # Add ZMQ publishing logic here if needed.
        pass
    else:
        print("Unknown output mode.", file=sys.stderr)

# --- Processing Logic ---
def process_files():
    """Process input files line by line."""
    if not args.files:
        log("No input files provided. Exiting.")
        return

    stats["files"] = len(args.files)

    for filename in args.files:
        stats["fileno"] += 1
        log(f"Processing file: {filename}")
        try:
            with open(filename, "r") as file:
                for line in file:
                    stats["lines"] += 1
                    message = preprocess_line(line)
                    if message:
                        output_line(message)
                        stats["processed"] += 1
        except Exception as e:
            log(f"Error processing file {filename}: {e}")

    log(f"Processing completed. {stats['processed']} lines processed.")

# --- Statistics Thread ---
def stats_thread():
    """Periodically print stats to stderr."""
    while True:
        elapsed = time.time() - stats["start"]
        log(f"Processed: {stats['processed']} lines in {elapsed:.2f}s")
        time.sleep(5)

# --- Main Script Execution ---
if __name__ == "__main__":
    try:
        if args.do_stats:
            stats_event = Event()
            stats_thread = Thread(target=stats_thread, daemon=True)
            stats_thread.start()

        process_files()
    except KeyboardInterrupt:
        log("Interrupted by user.")
    finally:
        if args.do_stats:
            stats_event.set()
            stats_thread.join()
