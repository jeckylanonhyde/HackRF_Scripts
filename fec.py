# vim: set ts=4 sw=4 tw=0 et pm=:

import sys
import numpy as np

def listify(v):
    """Convert a binary string to a list of integers."""
    return np.array([int(x) for x in v], dtype=np.int8)

def stringify(v):
    """Convert a list of integers to a binary string."""
    return ''.join(map(str, v))

# Debug flag
debug = 0

# Polynomial definitions
POLYA = 0x6D
POLYB = 0x4F

# Convert polynomials to binary arrays
p1 = listify(f"{POLYA:07b}")
p2 = listify(f"{POLYB:07b}")

def set_poly(pa, pb):
    """Set the polynomials for encoding."""
    global p1, p2
    p1 = listify(f"{pa:07b}")
    p2 = listify(f"{pb:07b}")
    if len(p1) != len(p2):
        raise ValueError("set_poly: Polynomial lengths are not equal.")

# Initial bit buffer
initbb = np.zeros(len(p1), dtype=np.int8)

def set_initbb(buffer):
    """Set the initial bit buffer."""
    global initbb
    if len(buffer) != len(p1):
        raise ValueError(f"initbb: Buffer length must be {len(p1)}.")
    initbb = np.array(buffer, dtype=np.int8)

def fec(bits):
    """Forward Error Correction (FEC) encoding."""
    bb = initbb.copy()
    out = []
    for bit in bits:
        if debug:
            print(f"Input bit: {bit}, Bit buffer: {bb}")
        bb = np.roll(bb, -1)
        bb[-1] = bit

        o1 = np.dot(p1, bb) % 2
        o2 = np.dot(p2, bb) % 2

        if debug:
            print(f"o1: {o1}, o2: {o2}")
        out.extend([o1, o2])
    return out

# Depuncture patterns
patterns = {
    "d1a": [1, 0, 1, 1, 1, 0],
    "d1b": [0, 1, 1, 1, 0, 1],
    "d1c": [1, 1, 1, 0, 1, 0],
    "d1d": [1, 1, 0, 1, 0, 1],
    "d1e": [1, 0, 1, 0, 1, 1],
    "d1f": [0, 1, 0, 1, 1, 1],
    "d2a": [1, 1, 0, 1, 1, 0],
    "d2b": [1, 0, 1, 1, 0, 1],
    "d2c": [0, 1, 1, 0, 1, 1],
    "d3a": [1, 1, 1, 0, 0, 1],
    "d3b": [1, 1, 0, 0, 1, 1],
    "d3c": [1, 0, 0, 1, 1, 1],
    "d3d": [0, 0, 1, 1, 1, 1],
    "d3e": [0, 1, 1, 1, 1, 0],
    "d3f": [1, 1, 1, 1, 0, 0]
}

def puncture(dp, bits):
    """Puncture the bit sequence according to the depuncture pattern."""
    dp = np.array(dp, dtype=bool)
    ostr = ''.join(str(bit) if dp[i % len(dp)] else '.' for i, bit in enumerate(bits))
    return ostr

# Example usage
if __name__ == "__main__":
    # Example setup and usage
    set_poly(POLYA, POLYB)
    set_initbb([0, 0, 0, 0, 0, 0, 0])
    input_bits = listify("1011001")
    encoded = fec(input_bits)
    print("Encoded bits:", stringify(encoded))

    punctured = puncture(patterns["d1a"], encoded)
    print("Punctured bits:", punctured)