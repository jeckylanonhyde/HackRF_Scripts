#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 tw=0 et fenc=utf8 pm=:

import sys
import fileinput
from util import myhex

def chunks(data, n):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), n):
        yield data[i:i + n]

def turn_symbols(byte):
    """Flip bit pairs in a byte."""
    out = 0
    if byte & 0x01:
        out |= 0x02
    if byte & 0x02:
        out |= 0x01
    if byte & 0x04:
        out |= 0x08
    if byte & 0x08:
        out |= 0x04
    if byte & 0x10:
        out |= 0x20
    if byte & 0x20:
        out |= 0x10
    if byte & 0x40:
        out |= 0x80
    if byte & 0x80:
        out |= 0x40
    return out

def process_line(line):
    """Process a single line of input."""
    line_parts = line.split()
    if line_parts[0] != 'VOD:':
        return None

    ts = float(line_parts[2])
    if int(line_parts[6]) < 179:
        return None

    data_index = 9 if line_parts[9][0] == "[" else 10
    data = line_parts[data_index]

    content = bytearray()
    for pos in range(1, len(data), 3):
        byte = int(data[pos:pos + 2], 16)
        byte = int(f'{byte:08b}'[::-1], 2)
        content.append(byte)

    return ts, content

def extract_frames(ts, content, ts_old, a_seq, a_data, b_seq, b_data, outfile):
    """Extract frames and write output if valid."""
    hdr = f'{content[0]:08b}'[::-1]
    content = content[1:]

    print(hdr, "".join(f"{x:02x}" for x in content), end=' ')

    if hdr.startswith(("11000", "10000", "01000")):
        print("A1", end=' ')
        a_seq = hdr[5:8]
        a_data = content[0:29]
        a_ts = ts
    elif hdr.startswith("00001"):
        print("B1", end=' ')
        b_seq = hdr[5:8]
        b_data = content[20:30]
        b_ts = ts
    elif hdr.startswith("00010"):
        print("B2", end=' ')
        b_seq = hdr[5:8]
        b_data = content[10:20]
        b_ts = ts
    elif hdr.startswith("00100"):
        print("B3", end=' ')
        b_seq = hdr[5:8]
        b_data = content[0:10]
        b_ts = ts
    else:
        return a_seq, a_data, b_seq, b_data, ts_old

    print("> ", a_seq, b_seq, end=' ')

    if a_seq and b_seq and a_seq == b_seq and abs(a_ts - b_ts) < 3 * 90:
        combined_data = a_data + b_data
        print('XXX: ', myhex(combined_data, '.'))

        if combined_data[0] == 0x03 and combined_data[1] == 0xc0:
            print(a_ts - ts_old, myhex(combined_data, '.'))

        outfile.write(combined_data)
        ts_old = a_ts
        a_seq, b_seq, a_data, b_data = None, None, '', ''

    print("")
    return a_seq, a_data, b_seq, b_data, ts_old

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 3:
        print("Usage: script.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    a_seq, b_seq = None, None
    a_data, b_data = '', ''
    ts_old = 0

    with open(output_file, 'wb') as outfile:
        for line in fileinput.input(input_file):
            result = process_line(line)
            if not result:
                continue

            ts, content = result
            a_seq, a_data, b_seq, b_data, ts_old = extract_frames(
                ts, content, ts_old, a_seq, a_data, b_seq, b_data, outfile
            )

if __name__ == "__main__":
    main()