#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 tw=0 et fenc=utf8 pm=:

import sys
import os
from util import parse_channel


class Frame:
    """Represents a single frame of data."""
    def __init__(self, frequency, alt_frequency, timestamp, line):
        self.frequency = frequency
        self.alt_frequency = alt_frequency
        self.timestamp = timestamp
        self.line = line


def process_file(file_path):
    """
    Process the input file to group frames into calls.
    
    Args:
        file_path (str): Path to the input file.
        
    Returns:
        list: List of grouped calls.
    """
    calls = []

    with open(file_path, "r") as file:
        for line in file:
            if "VOD: " not in line:
                continue

            parts = line.split()
            timestamp = float(parts[2]) / 1000.0  # Convert to seconds
            frequency = parse_channel(parts[3]) / 1000.0
            frame = Frame(frequency, 0, timestamp, line)

            for call in calls:
                last_frame = call[-1]

                # If the last frame is not more than 140 kHz and 20 seconds "away"
                if (
                    abs(last_frame.frequency - frame.frequency) < 140
                    and abs(last_frame.timestamp - frame.timestamp) < 20
                ):
                    call.append(frame)
                    break
            else:
                # Create a new call if no existing one matches
                calls.insert(0, [frame])

    return calls


def analyze_calls(calls):
    """
    Analyze calls and save to appropriate files based on voice detection.
    
    Args:
        calls (list): List of grouped calls.
    """
    call_id = 0

    for call in reversed(calls):
        # Skip calls shorter than 1 second
        if abs(call[0].timestamp - call[-1].timestamp) < 1:
            continue

        samples = [frame.line for frame in call]
        filename = f"call-{call_id:04d}.parsed"

        with open(filename, "w") as file:
            file.writelines(samples)

        # Analyze the call for voice detection
        is_voice = os.system(f"check-sample-vod {filename}") == 0

        # Rename file based on analysis result
        if not is_voice:
            os.rename(filename, f"fail-{call_id:04d}.parsed")

        call_id += 1


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: script.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    calls = process_file(input_file)
    analyze_calls(calls)


if __name__ == "__main__":
    main()