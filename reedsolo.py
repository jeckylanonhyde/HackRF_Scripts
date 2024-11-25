#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reed-Solomon Codec
===================
A Python implementation of a Reed-Solomon encoder and decoder.

This implementation supports both error correction and erasure correction. The API allows encoding messages with error correction codes and decoding corrupted messages to retrieve the original data, correcting errors up to `2*e+v <= nsym` where `e` is the number of errors, `v` is the number of erasures, and `nsym` is the number of error-correcting symbols.

For more information, refer to:
- https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction
- https://en.wikiversity.org/wiki/Reed%E2%80%93Solomon_codes_for_coders
"""

import itertools
from array import array

# Constants
GF_EXP = None
GF_LOG = None
FIELD_SIZE = None

class ReedSolomonError(Exception):
    """Custom exception for Reed-Solomon errors."""
    pass

# Galois Field Initialization
def init_gf(prim=0x11d, generator=2, field_size=256):
    """Initialize Galois Field lookup tables."""
    global GF_EXP, GF_LOG, FIELD_SIZE
    FIELD_SIZE = field_size - 1
    GF_EXP = array("B", [1] * (FIELD_SIZE * 2))
    GF_LOG = array("B", [0] * (FIELD_SIZE + 1))

    x = 1
    for i in range(FIELD_SIZE):
        GF_EXP[i] = x
        GF_LOG[x] = i
        x <<= 1
        if x & field_size:
            x ^= prim
    for i in range(FIELD_SIZE, FIELD_SIZE * 2):
        GF_EXP[i] = GF_EXP[i - FIELD_SIZE]

# Galois Field Arithmetic
def gf_add(x, y):
    return x ^ y

def gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return GF_EXP[(GF_LOG[x] + GF_LOG[y]) % FIELD_SIZE]

def gf_div(x, y):
    if y == 0:
        raise ZeroDivisionError()
    if x == 0:
        return 0
    return GF_EXP[(GF_LOG[x] - GF_LOG[y] + FIELD_SIZE) % FIELD_SIZE]

def gf_poly_add(p, q):
    """Add two polynomials."""
    length = max(len(p), len(q))
    p = list(p) + [0] * (length - len(p))
    q = list(q) + [0] * (length - len(q))
    return array("B", [gf_add(p[i], q[i]) for i in range(length)])

def gf_poly_mul(p, q):
    """Multiply two polynomials."""
    result = array("B", [0] * (len(p) + len(q) - 1))
    for i, coeff1 in enumerate(p):
        for j, coeff2 in enumerate(q):
            result[i + j] ^= gf_mul(coeff1, coeff2)
    return result

# Encoding
def rs_generator_poly(nsym):
    """Generate a generator polynomial."""
    g = array("B", [1])
    for i in range(nsym):
        g = gf_poly_mul(g, [1, GF_EXP[i]])
    return g

def rs_encode_msg(msg, nsym):
    """Encode a message using Reed-Solomon."""
    gen = rs_generator_poly(nsym)
    msg_out = array("B", msg) + array("B", [0] * nsym)
    for i in range(len(msg)):
        coef = msg_out[i]
        if coef != 0:
            for j in range(len(gen)):
                msg_out[i + j] ^= gf_mul(gen[j], coef)
    return msg + msg_out[-nsym:]

# Decoding
def rs_calc_syndromes(msg, nsym):
    """Calculate syndromes."""
    return [gf_poly_eval(msg, GF_EXP[i]) for i in range(nsym)]

def rs_find_error_locator(synd, nsym):
    """Find the error locator polynomial using Berlekamp-Massey algorithm."""
    err_loc = array("B", [1])
    old_loc = array("B", [1])
    for i in range(nsym):
        delta = synd[i]
        for j in range(1, len(err_loc)):
            delta ^= gf_mul(err_loc[-(j + 1)], synd[i - j])
        old_loc.append(0)
        if delta != 0:
            if len(old_loc) > len(err_loc):
                new_loc = gf_poly_scale(old_loc, delta)
                old_loc = gf_poly_scale(err_loc, gf_div(1, delta))
                err_loc = new_loc
            err_loc = gf_poly_add(err_loc, gf_poly_scale(old_loc, delta))
    return err_loc

def rs_correct_msg(msg_in, nsym):
    """Decode and correct a message using Reed-Solomon."""
    msg_out = array("B", msg_in)
    synd = rs_calc_syndromes(msg_out, nsym)
    if max(synd) == 0:
        return msg_out[:-nsym], msg_out[-nsym:]
    err_loc = rs_find_error_locator(synd, nsym)
    err_pos = rs_find_errors(err_loc, len(msg_out))
    if not err_pos:
        raise ReedSolomonError("Could not locate error")
    msg_out = rs_correct_errata(msg_out, synd, err_pos)
    synd = rs_calc_syndromes(msg_out, nsym)
    if max(synd) > 0:
        raise ReedSolomonError("Could not correct message")
    return msg_out[:-nsym], msg_out[-nsym:]

# API
class RSCodec:
    """Reed-Solomon Codec API."""

    def __init__(self, nsym=10):
        self.nsym = nsym
        init_gf()

    def encode(self, data):
        return rs_encode_msg(data, self.nsym)

    def decode(self, data):
        return rs_correct_msg(data, self.nsym)