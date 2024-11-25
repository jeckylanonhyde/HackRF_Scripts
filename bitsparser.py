#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import struct
import fileinput
import datetime
import numpy as np
from math import log

# Constants
IRIDIUM_ACCESS = "001100000011000011110011"
UPLINK_ACCESS = "110011000011110011111100"
UW_DOWNLINK = np.array([0, 2, 2, 2, 2, 0, 0, 0, 2, 0, 0, 2], dtype=np.uint8)
UW_UPLINK = np.array([2, 2, 0, 0, 0, 2, 0, 0, 2, 0, 2, 2], dtype=np.uint8)

MESSAGING_BCH_POLY = 1897
RINGALERT_BCH_POLY = 1207

F_DOPPLER = 36e3
F_JITTER = 1e3
SDR_PPM = 100e-6

F_SIMPLEX = (1626104e3 - F_DOPPLER - F_JITTER) * (1 - SDR_PPM)
F_DUPLEX = (1625979e3 + F_DOPPLER + F_JITTER) * (1 + SDR_PPM)


class ParserError(Exception):
    """Custom exception for parser-related errors."""
    pass


def reverse_bits(data: np.ndarray):
    """
    Reverse bits for each byte using vectorized operations.
    """
    lookup_table = np.array([int(f"{i:08b}"[::-1], 2) for i in range(256)], dtype=np.uint8)
    return lookup_table[data]


def de_interleave(bits: np.ndarray, step: int = 2):
    """
    De-interleave bits into separate arrays using NumPy slicing.
    """
    return bits[::step], bits[1::step]


def de_interleave3(bits: np.ndarray):
    """
    De-interleave bits into three streams using NumPy slicing.
    """
    return bits[::3], bits[1::3], bits[2::3]


def checksum_16(data: np.ndarray):
    """
    Compute a 16-bit checksum using NumPy for efficient summation.
    """
    csum = np.sum(data.view(np.uint16))
    csum = (csum & 0xFFFF) + (csum >> 16)  # Fold into 16 bits
    return csum ^ 0xFFFF


class Message:
    """
    Base class for parsing and handling messages.
    """

    def __init__(self, line):
        self.parse_line(line)

    def parse_line(self, line: str):
        """
        Parse a line of input data and extract fields.
        """
        pattern = re.compile(
            r'(RAW|RWA): ([^ ]*) (-?[\d.]+) (\d+) '
            r'(?:N:([+-]?\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)|A:(\w+)) [IL]:(\w+) +(\d+)% ([\d.]+|inf|nan) +(\d+) ([\[\]<> 01]+)(.*)'
        )
        match = pattern.match(line)
        if not match:
            raise ParserError(f"Unable to parse line: {line}")

        self.swapped = match.group(1) == "RAW"
        self.filename = match.group(2)
        self.timestamp = float(match.group(3))
        self.frequency = int(match.group(4))

        # Extract SNR or access_ok
        if match.group(5):
            self.snr = float(match.group(5))
            self.noise = float(match.group(6))
        else:
            self.access_ok = match.group(7) == "OK"

        self.id = match.group(8)
        self.confidence = int(match.group(9))
        self.level = max(float(match.group(10)), 1e-6)
        self.level_db = 20 * log(self.level, 10)

        # Process bitstream
        bitstream = re.sub(r"[\[\]<> ]", "", match.group(12))
        self.bitstream = np.array([int(bit) for bit in bitstream], dtype=np.uint8)
        if self.swapped:
            self.bitstream = reverse_bits(self.bitstream)

    def pretty(self):
        """
        Generate a human-readable string representation of the message.
        """
        return (f"RAW: {self.filename} ts={self.timestamp} "
                f"freq={self.frequency} id={self.id} "
                f"confidence={self.confidence}%")

    def extract_symbols(self):
        """
        Extract symbols by de-interleaving the bitstream.
        """
        if self.bitstream.size < len(IRIDIUM_ACCESS):
            raise ParserError("Bitstream too short to extract symbols.")
        symbols, extra = de_interleave(self.bitstream)
        return symbols, extra


class SymbolProcessor:
    """
    Class for processing symbols and handling BCH or ECC corrections.
    """

    def __init__(self, symbols: np.ndarray):
        self.symbols = symbols

    def correct_bch(self, poly):
        """
        Perform BCH error correction.
        """
        # Placeholder for BCH correction logic
        pass


def parse_input(input_file: str):
    """
    Parse the input file line by line.
    """
    messages = []
    for line in fileinput.input(input_file):
        try:
            message = Message(line.strip())
            messages.append(message)
        except ParserError as e:
            print(f"Error: {e}", file=sys.stderr)
    return messages


def main():
    """
    Main entry point for the script.
    """
    if len(sys.argv) < 2:
        print("Usage: script.py <input_file>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    messages = parse_input(input_file)

    for message in messages:
        print(message.pretty())


if __name__ == "__main__":
    main()