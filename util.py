#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 tw=0 et pm=:

import re
import sys
import types
import datetime
from math import atan2, sqrt, pi

# Define a UTC timezone class
class Zulu(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "Z"

Z = Zulu()

# Utility functions
def myhex(data, sep=''):
    """Convert byte data to a hexadecimal string with optional separator."""
    return sep.join(f"{x:02x}" for x in data)

def hex2bin(hexstr):
    """Convert a hexadecimal string to binary."""
    return f"{int(hexstr, 16):0{len(hexstr) * 4}b}"

def fmt_iritime(iritime):
    """Format Iridium epoch time to UTC."""
    base_time = 1399818235
    uxtime = iritime * 90 / 1000 + base_time
    # Adjust for leap seconds
    for leap in [1435708799, 1483228799]:
        if uxtime > leap:
            uxtime -= 1
    dt = datetime.datetime.fromtimestamp(uxtime, tz=Z)
    fractional = int((uxtime % 1) * 100)
    return uxtime, dt.strftime(f"%Y-%m-%dT%H:%M:%S.{fractional:02d}Z")

def grouped(iterable, n):
    """Group an iterable into chunks of size n."""
    return zip(*[iter(iterable)] * n)

def remove_zeros(lst):
    """Remove trailing zeros from a list."""
    while lst and not lst[-1]:
        lst.pop()

def group(string, n):
    """Group a string into n-length chunks."""
    return re.sub(f"(.{{{n}}})", r"\1 ", string).strip()

def slice_string(string, n):
    """Slice a string into n-length chunks."""
    return [string[i:i+n] for i in range(0, len(string), n)]

def to_ascii(data, dot=False, escape=False, mask=False):
    """Convert byte data to ASCII representation."""
    result = []
    for c in data:
        c = c & 0x7F if mask else c
        if 32 <= c < 127:
            result.append(chr(c))
        elif dot:
            result.append(".")
        elif escape:
            result.append(f"\\x{c:02x}" if c not in (0x0D, 0x0A) else ("\r" if c == 0x0D else "\n"))
        else:
            result.append(f"[{c:02x}]")
    return ''.join(result)

def bitdiff(a, b):
    """Count the number of differing bits between two binary strings."""
    return sum(x != y for x, y in zip(a, b))

def objprint(obj):
    """Print non-method attributes of an object."""
    for attr_name in dir(obj):
        if not attr_name.startswith('_'):
            attr = getattr(obj, attr_name)
            if not isinstance(attr, types.MethodType):
                print(f"{attr_name}: {attr}")

def curses_eol(file=sys.stderr):
    """Get the terminal's end-of-line capabilities."""
    import curses
    curses.setupterm(fd=file.fileno())
    el = curses.tigetstr('el') or b''
    cr = curses.tigetstr('cr') or b'\r'
    nl = curses.tigetstr('nl') or b'\n'
    eol = (el + cr).decode("ascii") if el else nl.decode("ascii")
    eolnl = (el + nl).decode("ascii") if el else nl.decode("ascii")
    return eol

# Position calculations
def xyz(data, skip=0):
    """Extract and calculate x/y/z position from 5 bytes."""
    value = int(data[:5].hex(), 16)
    shift_bits = 4 - skip

    def extract_coord(offset):
        coord = (value >> (12 * offset + shift_bits)) & 0xFFF
        return coord - 0x1000 if coord > 0x800 else coord

    loc_x, loc_y, loc_z = (extract_coord(i) for i in range(2, -1, -1))
    lat = atan2(loc_z, sqrt(loc_x ** 2 + loc_y ** 2)) * 180 / pi
    lon = atan2(loc_y, loc_x) * 180 / pi
    alt = sqrt(loc_x ** 2 + loc_y ** 2 + loc_z ** 2) * 4

    return {"x": loc_x, "y": loc_y, "z": loc_z, "lat": lat, "lon": lon, "alt": alt}

# Frequency calculations
BASE_FREQ = 1616 * 10**6
CHANNEL_WIDTH = 1e7 / (30 * 8)

def channelize(freq):
    """Convert frequency to channel and offset."""
    fbase = freq - BASE_FREQ
    freq_chan = int(fbase / CHANNEL_WIDTH)
    freq_off = fbase % CHANNEL_WIDTH - CHANNEL_WIDTH / 2
    return freq_chan, freq_off

def channelize_str(freq):
    """Convert frequency to channel and offset string."""
    fbase = freq - BASE_FREQ
    freq_chan = int(fbase / CHANNEL_WIDTH)
    subband = freq_chan // 8 + 1
    freq_access = freq_chan % 8 + 1
    freq_off = fbase % CHANNEL_WIDTH - CHANNEL_WIDTH / 2
    if subband > 30:
        return f"S.{freq_chan - 30 * 8 + 1:02}|{freq_off:+06.0f}"
    return f"{subband:02}.{freq_access}|{freq_off:+06.0f}"

def get_channel(subband, freq_access, strict=True):
    """Convert subband and frequency access to absolute frequency."""
    if subband == "S":
        subband = 31
    if strict:
        if not 0 <= int(subband) <= 31 or (int(subband) == 31 and not 0 <= int(freq_access) <= 12):
            raise ValueError(f"Invalid subband ({subband}) or frequency access ({freq_access})")
    return round(BASE_FREQ + CHANNEL_WIDTH / 2 + CHANNEL_WIDTH * 8 * (int(subband) - 1) + CHANNEL_WIDTH * (int(freq_access) - 1))

# Parsing utilities
def parse_handoff(lcw_str):
    """Parse handoff response from an LCW string."""
    fields = lcw_str[lcw_str.index("[")+1:lcw_str.index("]")].split(',')
    parsed = dict(field.split(':') for field in fields)
    parsed.update({k: int(v) for k, v in parsed.items() if v.isdigit()})
    return parsed

def parse_channel(fstr):
    """Parse frequency string to absolute frequency."""
    if "|" in fstr:
        chan, offset = fstr.split("|")
        if "." in chan:
            subband, freq_access = chan.split(".")
            return get_channel(subband, freq_access) + int(offset)
        return BASE_FREQ + CHANNEL_WIDTH * int(chan) + int(offset) + CHANNEL_WIDTH / 2
    return int(fstr)