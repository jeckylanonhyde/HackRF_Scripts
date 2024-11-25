#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 tw=0 et fenc=utf8 pm=:

import sys
import os
from util import parse_channel, parse_handoff, get_channel


class Frame:
    """Represents a frame in the data."""
    def __init__(self, frequency, alt_frequency, timestamp, line):
        self.frequency = frequency
        self.alt_frequency = alt_frequency
        self.timestamp = timestamp
        self.line = line


def process_file(file_path):
    """Process the input file to group frames into calls and analyze them."""
    calls = []

    # Process each line in the file
    with open(file_path, "r") as file:
        for line in file:
            if 'VOC: ' not in line:
                continue

            parts = line.split()
            timestamp = float(parts[2]) / 1000.0  # Convert to seconds
            frequency = parse_channel(parts[3]) / 1000.0
            frame = Frame(frequency, 0, timestamp, line)

            # Try to match the frame to an existing call
            for call in calls:
                last_frame = call[-1]

                if (
                    (
                        last_frame.alt_frequency and
                        abs(last_frame.alt_frequency - frame.frequency) < 40
                    ) or abs(last_frame.frequency - frame.frequency) < 20
                ) and abs(last_frame.timestamp - frame.timestamp) < 20:
                    if "handoff_resp" in parts[8]:
                        handoff = parse_handoff(parts[8])
                        frame.alt_frequency = (
                            get_channel(handoff["sband_dn"], handoff["access"]) / 1000.0
                            + 52
                        )

                    call.append(frame)
                    break
            else:
                # Create a new call if no existing one matches
                calls.insert(0, [frame])

    return calls


def save_and_analyze_calls(calls):
    """Save and analyze calls."""
    call_id = 0

    for call in reversed(calls):
        # Skip calls shorter than 1 second
        if abs(call[0].timestamp - call[-1].timestamp) < 1:
            continue

        samples = [frame.line for frame in call]
        filename = f"call-{call_id:04d}.parsed"

        # Write the samples to a file
        with open(filename, "w") as output_file:
            output_file.writelines(samples)

        # Analyze the samples
        result = os.system(f"check-sample {filename}") >> 8
        if result not in (0, 1):
            print(f"Problem running check-sample: {result}", file=sys.stderr)
            break

        # Rename file based on analysis result
        if result == 0:
            is_voice = True
        else:
            is_voice = False

        if not is_voice:
            os.rename(filename, f"fail-{call_id:04d}.parsed")

        call_id += 1


def main():
    if len(sys.argv) < 2:
        print("Usage: script.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    calls = process_file(input_file)
    save_and_analyze_calls(calls)


if __name__ == "__main__":
    main()