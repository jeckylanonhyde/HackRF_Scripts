#!/usr/bin/env python3
# A streamlined BCH error correction module with improved readability and maintainability.

from fec import stringify, listify

# Global storage for syndromes
syndromes = {}

# --- Utility Functions ---
def nndivide(poly, num):
    """Perform division in GF(2) (binary finite field)."""
    if num == 0:
        return 0
    shift = num.bit_length() - poly.bit_length()
    mask = 1 << (num.bit_length() - 1)

    while shift >= 0:
        if num >= mask:
            num ^= (poly << shift)
        mask >>= 1
        shift -= 1
    return num

def ndivide(poly, bits):
    """Perform division in GF(2) with binary string input."""
    num = int(bits, 2)
    return nndivide(poly, num)

def divide(a, b):
    """Binary GF(2) division with string inputs."""
    return nndivide(int(a, 2), int(b, 2))

def multiply(a, b):
    """Perform multiplication in GF(2)."""
    result = 0
    idx = 0
    while b > 0:
        if b % 2:
            result ^= (a << idx)
        b >>= 1
        idx += 1
    return result

def polystr(binary_str):
    """Convert a binary string to polynomial notation."""
    terms = [f"x^{len(binary_str) - 1 - i}" for i, bit in enumerate(binary_str) if bit == "1"]
    return " + ".join(terms)

def poly(a):
    """Convert an integer to polynomial notation."""
    return polystr(f"{a:b}")

# --- BCH Error Correction ---
def repair(poly, b):
    """Repair bit errors using brute-force method."""
    remainder = nndivide(poly, int(b, 2))
    if remainder == 0:
        return 0, b

    blen = len(b)
    bnum = int(b, 2)

    for b1 in range(blen):
        modified = bnum ^ (1 << b1)
        if nndivide(poly, modified) == 0:
            return 1, f"{modified:0{blen}b}"

    for b1 in range(blen):
        for b2 in range(b1 + 1, blen):
            modified = bnum ^ (1 << b1) ^ (1 << b2)
            if nndivide(poly, modified) == 0:
                return 2, f"{modified:0{blen}b}"

    return -1, b

def mk_syn(poly, bits, synbits, errors=1, debug=False):
    """Generate syndromes for BCH error correction."""
    assert errors in (1, 2, 3)
    syndromes[poly] = [None] * (2 ** synbits)

    if debug:
        print(f"Generating syndromes for poly={poly}, bits={bits}, max errors={errors}")

    for n1 in range(bits):
        val = 1 << n1
        r = nndivide(poly, val)
        syndromes[poly][r] = (1, val)

    if errors >= 2:
        for n1 in range(bits):
            for n2 in range(n1 + 1, bits):
                val = (1 << n1) | (1 << n2)
                r = nndivide(poly, val)
                if syndromes[poly][r] is None:
                    syndromes[poly][r] = (2, val)
                elif debug:
                    print(f"Collision detected: poly={poly}, syndrome={r}")

# --- Initialization ---
def init(debug=False):
    """Initialize BCH error correction syndromes."""
    mk_syn(poly=29, bits=7, synbits=4, debug=debug)
    mk_syn(poly=465, bits=14, synbits=8, errors=2, debug=debug)
    mk_syn(poly=41, bits=26, synbits=5, debug=debug)
    mk_syn(poly=1897, bits=31, synbits=10, errors=2, debug=debug)
    mk_syn(poly=1207, bits=31, synbits=10, errors=2, debug=debug)
    mk_syn(poly=3545, bits=31, synbits=11, errors=2, debug=debug)

# --- Main Execution ---
if __name__ == "__main__":
    init(debug=True)
else:
    init()
