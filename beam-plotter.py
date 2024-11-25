#!/usr/bin/env python3

import sys
import math
import matplotlib.pyplot as plt
import numpy as np
from argparse import ArgumentParser

# --- Constants ---
INCLINATION_DEG = 84.0
HIGH_ALTITUDE_THRESHOLD = 7000  # in km
TIME_THRESHOLD = 10  # in seconds

# --- Argument Parsing ---
def parse_arguments():
    parser = ArgumentParser(description="Generate beam patterns from Iridium data.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-d", "--direction", type=str, help="Specify direction: 'n' (north) or 's' (south)"
    )
    parser.add_argument(
        "-s", "--sat", type=int, help="Specify satellite number to filter data"
    )
    parser.add_argument(
        "files", nargs="*", help="Input files with satellite data"
    )
    return parser.parse_args()

# --- Helper Functions ---
def convert_to_km(value):
    """Convert position from raw units to kilometers."""
    return int(value) * 4

def calculate_lat_lon_alt(x, y, z):
    """Calculate latitude, longitude, and altitude."""
    lat = math.atan2(z, math.sqrt(x**2 + y**2)) * 180 / math.pi
    lon = math.atan2(y, x) * 180 / math.pi
    alt = math.sqrt(x**2 + y**2 + z**2)
    return lat, lon, alt

def debug_message(verbose, message):
    """Print debug messages if verbose mode is enabled."""
    if verbose:
        print(message)

# --- Data Processing ---
def process_data_line(line, config, xs, ys, seen, north, pos):
    sat, cell, x, y, z, nstime = line.split(None, 6)
    sat = int(sat)
    cell = int(cell)
    
    if config.sat and sat != config.sat:
        return

    # Convert position to kilometers
    x, y, z = convert_to_km(x), convert_to_km(y), convert_to_km(z)
    lat, lon, alt = calculate_lat_lon_alt(x, y, z)
    gtime = float(nstime) / 1e10  # Convert nanoseconds to seconds

    if alt > HIGH_ALTITUDE_THRESHOLD:
        handle_high_altitude(sat, x, y, z, gtime, seen, north, pos, config.verbose)
    else:
        handle_low_altitude(
            sat, cell, x, y, z, gtime, xs, ys, seen, north, pos, config
        )

def handle_high_altitude(sat, x, y, z, gtime, seen, north, pos, verbose):
    debug_message(verbose, f"Processing high-altitude satellite {sat}")
    if seen[sat] > 0 and (gtime - seen[sat]) < TIME_THRESHOLD:
        ox, oy, oz = pos[sat]
        if z - oz != 0:
            north[sat] = 1 if (z - oz) > 0 else -1
    else:
        north[sat] = 0
    seen[sat] = gtime
    pos[sat] = (x, y, z)

def handle_low_altitude(sat, cell, x, y, z, gtime, xs, ys, seen, north, pos, config):
    debug_message(config.verbose, f"Processing low-altitude satellite {sat}")
    if not seen[sat] or (gtime - seen[sat]) > TIME_THRESHOLD or north[sat] == 0:
        return

    if config.direction and config.direction != north[sat]:
        return

    ox, oy, oz = pos[sat]
    lat, lon, _ = calculate_lat_lon_alt(ox, oy, oz)

    inclination_rad = math.radians(-(90 - INCLINATION_DEG))
    if north[sat] < 0:
        inclination_rad = math.radians(-(180 - (90 - INCLINATION_DEG)))

    # Apply rotation transformations
    x3, y3, z3 = apply_transformations(x, y, z, lat, lon, inclination_rad)
    xs[cell].append(y3)
    ys[cell].append(z3)

def apply_transformations(x, y, z, lat, lon, inclination):
    """Rotate coordinates to the correct frame."""
    # Rotate longitude to zero (around z-axis)
    x1 = x * math.cos(-math.radians(lon)) - y * math.sin(-math.radians(lon))
    y1 = x * math.sin(-math.radians(lon)) + y * math.cos(-math.radians(lon))
    z1 = z

    # Rotate latitude to equator (around y-axis)
    x2 = x1 * math.cos(-math.radians(lat)) - z1 * math.sin(-math.radians(lat))
    y2 = y1
    z2 = x1 * math.sin(-math.radians(lat)) + z1 * math.cos(-math.radians(lat))

    # Rotate by inclination (around x-axis)
    x3 = x2
    y3 = y2 * math.cos(-inclination) - z2 * math.sin(-inclination)
    z3 = y2 * math.sin(-inclination) + z2 * math.cos(-inclination)
    return x3, y3, z3

# --- Plotting ---
def plot_data(xs, ys, config):
    colormap = plt.cm.gist_ncar
    colors = [colormap(i) for i in np.linspace(0, 0.9, len(xs))]
    
    for cell, x_vals in enumerate(xs):
        if not x_vals:
            continue
        y_vals = ys[cell]
        xc, yc = np.mean(x_vals), np.mean(y_vals)
        max_dist = max(
            math.sqrt((x - xc)**2 + (y - yc)**2) for x, y in zip(x_vals, y_vals)
        )
        plt.gca().add_artist(plt.Circle((xc, yc), max_dist + 10, color=colors[cell], fill=False))
        plt.scatter(x_vals, y_vals, color=colors[cell], label=f"Cell {cell} ({len(x_vals)})")
        plt.annotate(str(cell), (xc + max_dist + 10, yc + max_dist + 10))

    plt.xlabel("Y (km)")
    plt.ylabel("Z (km)")
    plt.gca().set_aspect("equal", "datalim")
    plt.legend(fontsize="small")
    plt.title(generate_plot_title(config))
    plt.tight_layout()
    plt.show()

def generate_plot_title(config):
    title = "Beam Pattern Plot"
    if config.sat:
        title += f" for Sat {config.sat}"
    if config.direction == 1:
        title += " (North)"
    elif config.direction == -1:
        title += " (South)"
    return title

# --- Main Execution ---
def main():
    config = parse_arguments()

    xs = [[] for _ in range(50)]
    ys = [[] for _ in range(50)]
    seen = [0] * 255
    north = [0] * 255
    pos = [None] * 255

    for file in config.files:
        with open(file, "r") as f:
            for line in f:
                process_data_line(line.strip(), config, xs, ys, seen, north, pos)

    plot_data(xs, ys, config)

if __name__ == "__main__":
    main()
