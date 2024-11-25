#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import fileinput
import sys

def turn_symbols(byte):
    """
    Reverse specific bit positions in a byte.
    """
    out = ((byte & 0x01) << 1) | ((byte & 0x02) >> 1) | \
          ((byte & 0x04) << 1) | ((byte & 0x08) >> 1) | \
          ((byte & 0x10) << 1) | ((byte & 0x20) >> 1) | \
          ((byte & 0x40) << 1) | ((byte & 0x80) >> 1)
    return out

def chunks(data, size):
    """
    Yield successive chunks of the specified size from data.
    """
    for i in range(0, len(data), size):
        yield data[i:i+size]

def process_voc_lines(input_file, output_file):
    """
    Process VOC lines from the input file and write the processed bytes to the output file.
    """
    with open(output_file, 'wb') as outfile:
        for line in fileinput.input(input_file):
            line_parts = line.split()
            if len(line_parts) < 11 or line_parts[0] != 'VOC:':
                continue

            # Filter by the length threshold
            if int(line_parts[6]) < 179:
                continue

            # Extract the data string
            data = line_parts[9] if line_parts[9].startswith("[") else line_parts[10]

            if data.startswith("["):
                # Process hex data
                for pos in range(1, len(data), 3):
                    byte = int(data[pos:pos+2], 16)
                    reversed_byte = int(f"{byte:08b}"[::-1], 2)
                    outfile.write(bytes([reversed_byte]))
            else:
                # Process binary data
                for bits in chunks(data, 8):
                    reversed_byte = int(bits[::-1], 2)
                    outfile.write(bytes([reversed_byte]))

def main():
    if len(sys.argv) != 3:
        print("Usage: script.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    process_voc_lines(input_file, output_file)

if __name__ == "__main__":
    main()