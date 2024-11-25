#!/usr/bin/env python3

import argparse
import re
import os
import sys
from math import sqrt, pi, cos, acos
from itertools import compress
from configparser import ConfigParser
import matplotlib.pyplot as plt
import numpy as np
import pyproj

# --- Constants ---
np.set_printoptions(floatmode='maxprec', suppress=True, precision=4)
ECEF = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
LLA = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')
TO_LLA = pyproj.Transformer.from_proj(ECEF, LLA)
TO_ECEF = pyproj.Transformer.from_proj(LLA, ECEF)
INC = 86.4 / 180 * pi  # Satellite inclination in radians
EPSILON = 1e-11
NORTH_POLE = np.array(TO_ECEF.transform(0, 90, 0, radians=False)) / 1000  # in km

# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(description="Plots beam reception relative to satellite position at a given location.")
    beams = {'outer': '5,10,1,38,43,36,23,19,18,25', 'inner': '32,31,48,47,16,15', 'mid': '12,24,28,40,44,8'}

    def parse_comma(arg):
        """Parse integers separated by commas or predefined groups."""
        return [int(x) for x in beams.get(arg, arg).split(',')]

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-b", "--beam", type=parse_comma, default=None, help="Beam(s) to plot")
    parser.add_argument("-d", "--direction", choices=['n', 's', 'b'], default='n', help="Direction of flight")
    parser.add_argument("-s", "--sat", type=int, help="Satellite to plot")
    parser.add_argument("-l", "--loc", choices=get_locations(), default="default", help="Observer location")
    parser.add_argument("--snr", type=int, default=25, help="SNR dB cutoff")
    parser.add_argument("files", nargs="*", help="Input files")
    return parser.parse_args()

# --- Configuration Handling ---
def get_locations():
    config = ConfigParser()
    config.read(['locations.ini', os.path.join(os.path.dirname(__file__), 'locations.ini')])
    if config.sections():
        return config.sections()
    sys.exit("locations.ini missing or empty")

def read_observer(location):
    config = ConfigParser()
    config.read(['locations.ini', os.path.join(os.path.dirname(__file__), 'locations.ini')])
    if location not in config:
        available = ", ".join(config.sections())
        sys.exit(f"Location '{location}' not defined. Available locations: {available}")

    section = config[location]
    observer = {'name': section.get('name', location)}

    if 'lat' in section and 'lon' in section and 'alt' in section:
        lat, lon, alt = section.getfloat('lat'), section.getfloat('lon'), section.getfloat('alt')
        observer['xyz'] = np.array(TO_ECEF.transform(lon, lat, alt, radians=False)) / 1000
    elif 'x' in section and 'y' in section and 'z' in section:
        x, y, z = section.getfloat('x'), section.getfloat('y'), section.getfloat('z')
        observer['xyz'] = np.array([x, y, z]) / 1000
    else:
        sys.exit(f"Location '{location}' lacks complete coordinates.")
    
    return observer

# --- Satellite Coordinate System ---
def incl_system(pos_sat, north):
    """Compute the satellite coordinate system based on inclination."""
    x, y, z = pos_sat
    sat_plane = pos_sat / np.linalg.norm(pos_sat)
    c = cos(INC)

    try:
        a1, b1, a2, b2 = solve_plane_equation(x, y, z, c)
        v1, v2 = np.array([a1, b1, c]), np.array([a2, b2, c])
    except (ValueError, ZeroDivisionError):
        return None

    orbit_plane = v2 if north > 0 else v1
    direction_vec = np.cross(sat_plane, orbit_plane)
    return sat_plane, orbit_plane, direction_vec

def solve_plane_equation(x, y, z, c):
    """Solve the orbital plane equation for given parameters."""
    if y != 0:
        a1 = -(c * x * z + sqrt(-c**2 * z**2 - (c**2 - 1) * x**2 - (c**2 - 1) * y**2) * y) / (x**2 + y**2)
        b1 = -(a1 * x + c * z) / y
        a2 = -(c * x * z - sqrt(-c**2 * z**2 - (c**2 - 1) * x**2 - (c**2 - 1) * y**2) * y) / (x**2 + y**2)
        b2 = -(a2 * x + c * z) / y
    else:
        b1 = -(c * y * z + sqrt(-c**2 * z**2 - (c**2 - 1) * x**2 - (c**2 - 1) * y**2) * x) / (x**2 + y**2)
        a1 = -(b1 * y + c * z) / x
        b2 = -(c * y * z - sqrt(-c**2 * z**2 - (c**2 - 1) * x**2 - (c**2 - 1) * y**2) * x) / (x**2 + y**2)
        a2 = -(b2 * y + c * z) / x
    return a1, b1, a2, b2

# --- Data Processing ---
def read_file(observer, args):
    xs, ys, ss = [[] for _ in range(50)], [[] for _ in range(50)], [[] for _ in range(50)]
    seen, north, pos = [0] * 255, [0] * 255, [None] * 255

    for line in fileinput.input(args.files):
        if not line.startswith("IRA:"):
            continue
        mm = re.match(r"IRA: .* (\d+) .* (\d+) xyz=.(.\d+),(.\d+),(.\d+)", line)
        if not mm:
            continue

        sat, cell, x, y, z = map(int, mm.groups())
        if args.sat and sat != args.sat:
            continue

        pos_sat = np.array([x * 4, y * 4, z * 4])
        sat_system = incl_system(pos_sat, north[sat])
        if not sat_system:
            continue

        res = transform_to_observer(observer['xyz'], sat_system, pos_sat)
        xs[cell].append(res[1])
        ys[cell].append(res[2])
        ss[cell].append(args.snr)

    return xs, ys, ss

def transform_to_observer(observer_xyz, sat_system, pos_sat):
    """Transform coordinates to observer-relative system."""
    sat_plane, orbit_plane, direction_vec = sat_system
    F = np.eye(4)
    F[:3, :3] = np.array([sat_plane, orbit_plane, direction_vec])
    F[:3, 3] = -observer_xyz
    return np.dot(F, np.append(pos_sat, 1))[:3]

# --- Plotting ---
def plot_data(xs, ys, ss, args):
    plt.xlabel('Y (km)')
    plt.ylabel('Z (km)')
    colormap = plt.cm.gist_ncar
    colors = [colormap(i) for i in np.linspace(0, 0.9, len(xs))]

    for cell, (x, y, s) in enumerate(zip(xs, ys, ss)):
        if not x:
            continue
        selectors = [snr > args.snr for snr in s]
        plt.scatter(
            x=list(compress(x, selectors)),
            y=list(compress(y, selectors)),
            color=colors[cell],
            label=f"Cell {cell} ({len(list(compress(x, selectors)))})",
        )

    plt.title("Beam Reception")
    plt.legend(fontsize='small')
    plt.gca().set_aspect('equal', 'datalim')
    plt.tight_layout()
    plt.show()

# --- Main ---
if __name__ == "__main__":
    args = parse_arguments()
    observer = read_observer(args.loc)
    xs, ys, ss = read_file(observer, args)
    plot_data(xs, ys, ss, args)
