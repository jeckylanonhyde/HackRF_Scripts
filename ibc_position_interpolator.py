#!/usr/bin/env python3
import sys
import datetime
from math import sqrt
import numpy as np
import pymap3d
import interp_circ

debug = False
tlefile = 'tracking/iridium-NEXT.txt'
tmax = 60e9
ppm = 0

class InterpException(Exception):
    """Custom exception for interpolation errors."""
    pass

# File inputs
ibc = open(sys.argv[1])
ira = open(sys.argv[2])

# Initialize arrays
maxsat = 127
ira_xyzt = [[np.zeros(4)] for _ in range(maxsat)]
ira_t = np.zeros(maxsat, dtype=int)

# Satellite indices for interpolation
satidx = np.zeros(maxsat, dtype=int)
osatidx = np.zeros(maxsat, dtype=int)

def read_ira():
    """Read and parse IRA data."""
    for line in ira:
        tu, s, b, alt, x, y, z = line.split(None, 7)
        s = int(s)
        x, y, z = int(x) * 4000, int(y) * 4000, int(z) * 4000
        tu = int(tu)

        x, y, z = pymap3d.ecef2eci(x, y, z, datetime.datetime.utcfromtimestamp(tu / 1e9))
        ira_xyzt[s].append([x, y, z, tu])

def interp_ira(sat, ts):
    """Interpolate satellite position using linear interpolation."""
    global satidx, osatidx

    if ts > ira_xyzt[sat][satidx[sat]][3]:
        satidx[sat] = 0

    if satidx[sat] == 0:
        osatidx[sat] = 0
        for idx, data in enumerate(ira_xyzt[sat]):
            if osatidx[sat] == 0 and ts - data[3] < tmax:
                osatidx[sat] = idx
            if data[3] - ts > tmax:
                break
            satidx[sat] = idx

    idx, idxo = satidx[sat], osatidx[sat]
    tn, to = ira_xyzt[sat][idx][3], ira_xyzt[sat][idxo][3]
    delta = tn - to

    if delta > 2000e9:
        raise InterpException("Too inaccurate (Δ=%d)" % delta)
    if ts < to or ts > tn:
        raise InterpException("Out of interpolation bounds")

    T = [t for _, _, _, t in ira_xyzt[sat][idxo:idx + 1]]
    X = [x for x, _, _, _ in ira_xyzt[sat][idxo:idx + 1]]
    Y = [y for _, y, _, _ in ira_xyzt[sat][idxo:idx + 1]]
    Z = [z for _, _, z, _ in ira_xyzt[sat][idxo:idx + 1]]

    if len(T) < 2:
        raise InterpException("Not enough data for interpolation")

    xyz = interp_circ.interp([X, Y, Z], T, ts, debug)
    xyz = pymap3d.eci2ecef(*xyz, datetime.datetime.utcfromtimestamp(ts / 1e9))
    return xyz

def main():
    """Main function to process IBC and IRA data."""
    read_ira()

    ys = []
    t0 = None

    for line in ibc:
        tu, ti, slot, s, b = line.split(None, 5)
        tu, slot, s = int(tu), int(slot), int(s)
        ti = int(float(ti) * 1e9)

        # Time correction based on slot
        if slot == 1:
            ti += 3 * (8280 + 100) * 1e6

        # PPM correction
        if t0 is None:
            t0 = tu
        tu = tu - (tu - t0) * ppm // 10**6

        try:
            xyz = interp_ira(s, tu)
            ys.append((tu, s, np.array(xyz), tu - ti))
            print(tu, s, xyz[0], xyz[1], xyz[2], tu - ti)
        except InterpException as e:
            if debug:
                print(f"Warning: {e}", file=sys.stderr)

    avg_delay = np.average([y[3] for y in ys])
    print(f"Average delay to system time: {avg_delay}", file=sys.stderr)

if __name__ == "__main__":
    main()