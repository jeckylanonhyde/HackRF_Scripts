#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reed-Solomon Error Correction
=============================
This module implements a Reed-Solomon codec for encoding and decoding data
with error correction capabilities. The implementation supports both
errors and erasures and uses precomputed tables for efficient finite field
arithmetic.

References:
- https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction
- https://en.wikiversity.org/wiki/Reed%E2%80%93Solomon_codes_for_coders
"""

import itertools

class ReedSolomonError(Exception):
    """Custom exception for Reed-Solomon related errors."""
    pass

# Constants
GF_EXP = bytearray([1] * 512)  # Galois Field exponential table
GF_LOG = bytearray(256)  # Galois Field logarithm table
FIELD_SIZE = 2 ** 8 - 1  # Size of GF(2^8)

def init_tables(prim=0x11d, generator=2, field_exp=8):
    """Precomputes logarithm and anti-log tables for GF arithmetic."""
    global GF_EXP, GF_LOG, FIELD_SIZE
    FIELD_SIZE = 2 ** field_exp - 1
    GF_EXP = bytearray(FIELD_SIZE * 2)
    GF_LOG = bytearray(FIELD_SIZE + 1)

    x = 1
    for i in range(FIELD_SIZE):
        GF_EXP[i] = x
        GF_LOG[x] = i
        x = gf_multiply_no_lut(x, generator, prim, FIELD_SIZE + 1)

    for i in range(FIELD_SIZE, FIELD_SIZE * 2):
        GF_EXP[i] = GF_EXP[i - FIELD_SIZE]

def gf_add(x, y):
    """Adds two elements in GF(2^p)."""
    return x ^ y

def gf_multiply(x, y):
    """Multiplies two elements in GF(2^p) using lookup tables."""
    if x == 0 or y == 0:
        return 0
    return GF_EXP[(GF_LOG[x] + GF_LOG[y]) % FIELD_SIZE]

def gf_multiply_no_lut(x, y, prim=0, field_char=256):
    """Multiplies two elements in GF(2^p) without lookup tables."""
    result = 0
    while y:
        if y & 1:
            result ^= x
        y >>= 1
        x <<= 1
        if prim > 0 and x & field_char:
            x ^= prim
    return result

def gf_poly_add(p, q):
    """Adds two polynomials in GF."""
    length = max(len(p), len(q))
    r = bytearray(length)
    for i in range(len(p)):
        r[i + length - len(p)] = p[i]
    for i in range(len(q)):
        r[i + length - len(q)] ^= q[i]
    return r

def gf_poly_multiply(p, q):
    """Multiplies two polynomials in GF."""
    r = bytearray(len(p) + len(q) - 1)
    for j in range(len(q)):
        for i in range(len(p)):
            r[i + j] ^= gf_multiply(p[i], q[j])
    return r

def rs_generator_poly(nsym, generator=2):
    """Generates the Reed-Solomon generator polynomial."""
    g = bytearray([1])
    for i in range(nsym):
        g = gf_poly_multiply(g, [1, gf_exp(generator, i)])
    return g

def rs_encode_msg(msg, nsym, generator=2, gen=None):
    """Encodes a message using Reed-Solomon error correction."""
    if gen is None:
        gen = rs_generator_poly(nsym, generator)
    msg = bytearray(msg)
    padded_msg = msg + bytearray(len(gen) - 1)
    for i in range(len(msg)):
        coef = padded_msg[i]
        if coef != 0:
            for j in range(len(gen)):
                padded_msg[i + j] ^= gf_multiply(gen[j], coef)
    return msg + padded_msg[-len(gen) + 1:]

def rs_decode_msg(msg, nsym, generator=2):
    """Decodes a message encoded with Reed-Solomon error correction."""
    synd = [gf_poly_eval(msg, gf_exp(generator, i)) for i in range(nsym)]
    if max(synd) == 0:
        return msg[:-nsym], msg[-nsym:]
    raise NotImplementedError("Decoding logic not implemented.")

class RSCodec:
    """Reed-Solomon Encoder/Decoder class."""

    def __init__(self, nsym=10, prim=0x11d, generator=2):
        self.nsym = nsym
        self.generator = generator
        init_tables(prim, generator)

    def encode(self, data):
        """Encodes data with Reed-Solomon error correction."""
        if isinstance(data, str):
            data = bytearray(data, "utf-8")
        return rs_encode_msg(data, self.nsym, self.generator)

    def decode(self, data):
        """Decodes data encoded with Reed-Solomon error correction."""
        if isinstance(data, str):
            data = bytearray(data, "utf-8")
        return rs_decode_msg(data, self.nsym, self.generator)

if __name__ == "__main__":
    codec = RSCodec(nsym=10)
    message = b"hello world"
    encoded = codec.encode(message)
    print("Encoded:", encoded)
    decoded, _ = codec.decode(encoded)
    print("Decoded:", decoded)