#!/usr/bin/env python3

import sys
import numpy as np
import pseudoranging
import pyproj

# Debugging flag
debug = False

# Coordinate transformation setup
ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')

to_lla = pyproj.Transformer.from_proj(ecef, lla, always_xy=True)
to_ecef = pyproj.Transformer.from_proj(lla, ecef, always_xy=True)

# Home location in LLA and ECEF
name = "Home"
lat, lon, alt = 33.951533, -84.728753, 339
ox, oy, oz = to_ecef.transform(lon, lat, alt)
observer = np.array((ox, oy, oz))

print(f"{name} Location (LLA):", lon, lat, alt)
print(f"{name} Location (ECEF):", ox, oy, oz)

# Open the input file
with open(sys.argv[1]) as ibc_pos:
    last_observation = {}
    last_result = np.zeros(3)
    good = []
    errors = []
    height_errors = []
    bad, known_bad = 0, 0

    for line in ibc_pos:
        tu, s, x, y, z, deltat = line.split(None, 5)
        tu = int(tu) / 1e9
        s = int(s)
        xyz = np.array([float(x), float(y), float(z)])
        dt = int(deltat) / 1e9

        # Update observation for satellite
        last_observation[s] = (tu, s, xyz, dt)

        # Filter observations within the last 60 seconds
        concurrent_observation = {
            lo[1]: lo for lo in last_observation.values() if tu - lo[0] < 60
        }

        # Proceed if enough observations are available
        if len(concurrent_observation) > 3:
            pseudoranges = [(obs[2], obs[3]) for obs in concurrent_observation.values()]
            result = last_result

            # Iterate to converge
            for _ in range(4):
                result = pseudoranging.solve(pseudoranges, result)

            # Validate result height
            height = np.linalg.norm(result)
            if abs(height - 6372e3) > 100e3:
                known_bad += 1
                continue

            last_result = result
            error = np.linalg.norm(result - observer)
            height_error = height - np.linalg.norm(observer)

            print(f"Error: {int(error)} ({int(height_error)}) {result}")

            if error < 10_000:
                good.append(result)
                errors.append(error)
                height_errors.append(height_error)
            else:
                bad += 1

# Summary statistics
print("good:", len(good), "bad:", bad, "known_bad:", known_bad)

if good:
    avg_error = np.average(errors)
    avg_height_error = np.average(height_errors)
    average_position = np.average(good, axis=0)

    print("Average Cartesian Error:", avg_error, "(", avg_height_error, ")")
    print("Average Cartesian Position:", average_position)
    print("Average Cartesian Position Error:", np.linalg.norm(average_position - observer))
    print("Average Cartesian Position Height Error:", np.linalg.norm(average_position) - np.linalg.norm(observer))

    # Convert average position to LLA
    avg_lat, avg_lon, avg_alt = to_lla.transform(
        average_position[0], average_position[1], average_position[2]
    )
    print("Average Cartesian Position to LLA:", avg_lon, avg_lat, avg_alt)
else:
    print("No valid solutions found.")