#!/usr/bin/env python3

from ctypes import (
    c_void_p,
    c_char_p,
    c_char,
    c_int,
    c_size_t,
    c_bool,
    c_long,
    Structure,
    POINTER,
    CDLL,
    cast,
)
from enum import IntEnum, auto


class CtypesEnum(IntEnum):
    """A ctypes-compatible IntEnum superclass."""
    @classmethod
    def from_param(cls, obj):
        return int(obj)


class la_msg_dir(CtypesEnum):
    LA_MSG_DIR_UNKNOWN = 0
    LA_MSG_DIR_GND2AIR = auto()
    LA_MSG_DIR_AIR2GND = auto()


class la_reasm_status(CtypesEnum):
    LA_REASM_UNKNOWN = 0
    LA_REASM_COMPLETE = auto()
    LA_REASM_IN_PROGRESS = auto()
    LA_REASM_SKIPPED = auto()
    LA_REASM_DUPLICATE = auto()
    LA_REASM_FRAG_OUT_OF_SEQUENCE = auto()
    LA_REASM_ARGS_INVALID = auto()


class timeval(Structure):
    _fields_ = [("tv_sec", c_long), ("tv_usec", c_long)]


class la_type_descriptor(Structure):
    _fields_ = [
        ("format_text", c_void_p),
        ("destroy", c_void_p),
        ("format_json", c_void_p),
        ("json_key", c_char_p),
    ]


class la_acars_msg(Structure):
    _fields_ = [
        ("crc_ok", c_bool),
        ("err", c_bool),
        ("final_block", c_bool),
        ("mode", c_char),
        ("reg", c_char * 8),
        ("ack", c_char),
        ("label", c_char * 3),
        ("sublabel", c_char * 3),
        ("mfi", c_char * 3),
        ("block_id", c_char),
        ("msg_num", c_char * 4),
        ("msg_num_seq", c_char),
        ("flight_id", c_char * 7),
        ("reasm_status", c_int),
    ]


class la_proto_node(Structure):
    pass


la_proto_node._fields_ = [
    ("td", POINTER(la_type_descriptor)),
    ("data", c_void_p),
    ("next", POINTER(la_proto_node)),
]


class la_vstr(Structure):
    _fields_ = [
        ("str", c_char_p),
        ("len", c_size_t),
        ("allocated_size", c_size_t),
    ]


class libacars:
    lib = CDLL("libacars-2.so")
    version = cast(lib.LA_VERSION, POINTER(c_char_p)).contents.value.decode("ascii")

    # Define function signatures
    lib.la_acars_parse.restype = POINTER(la_proto_node)
    lib.la_acars_parse.argtypes = [c_char_p, c_size_t, la_msg_dir]

    lib.la_acars_parse_and_reassemble.restype = POINTER(la_proto_node)
    lib.la_acars_parse_and_reassemble.argtypes = [c_char_p, c_size_t, la_msg_dir, c_void_p, timeval]

    lib.la_proto_tree_format_text.restype = POINTER(la_vstr)
    lib.la_proto_tree_format_text.argtypes = [c_void_p, POINTER(la_proto_node)]

    lib.la_proto_tree_format_json.restype = POINTER(la_vstr)
    lib.la_proto_tree_format_json.argtypes = [c_void_p, POINTER(la_proto_node)]

    lib.la_vstring_destroy.restype = None
    lib.la_vstring_destroy.argtypes = [POINTER(la_vstr), c_bool]

    lib.la_proto_tree_destroy.restype = None
    lib.la_proto_tree_destroy.argtypes = [POINTER(la_proto_node)]

    lib.la_reasm_ctx_new.restype = c_void_p
    lib.la_reasm_ctx_new.argtypes = []

    ctx = lib.la_reasm_ctx_new()

    def __init__(self, data, direction=la_msg_dir.LA_MSG_DIR_UNKNOWN, time=None):
        data = data[1:]
        if data[0] == 3:
            data = data[8:]  # Remove unknown Iridium header

        if time is None:
            self.p = libacars.lib.la_acars_parse(data, len(data), direction)
        else:
            timeval_obj = timeval(int(time), int((time - int(time)) * 1_000_000))
            self.p = libacars.lib.la_acars_parse_and_reassemble(
                data, len(data), direction, libacars.ctx, timeval_obj
            )

    def json(self):
        vstr = libacars.lib.la_proto_tree_format_json(None, self.p)
        result = vstr.contents.str.decode("ascii")
        libacars.lib.la_vstring_destroy(vstr, True)
        return result

    def is_err(self):
        if self.p.contents.td.contents.json_key != b"acars":
            return False
        return cast(self.p.contents.data, POINTER(la_acars_msg)).contents.err

    def is_ping(self):
        if self.p.contents.td.contents.json_key != b"acars":
            return False
        msg = cast(self.p.contents.data, POINTER(la_acars_msg)).contents
        return not msg.err and msg.label in (b'_d', b'Q0')

    def is_reasm(self):
        if self.p.contents.td.contents.json_key != b"acars":
            return False
        msg = cast(self.p.contents.data, POINTER(la_acars_msg)).contents
        return not msg.err and msg.reasm_status == la_reasm_status.LA_REASM_IN_PROGRESS

    def is_interesting(self):
        return self.p.contents.td.contents.json_key != b"acars" or self.p.contents.next

    def debug(self):
        print(f"Type Descriptor: {self.p.contents.td.contents.json_key}")
        print(f"Error: {cast(self.p.contents.data, POINTER(la_acars_msg)).contents.err}")
        if self.p.contents.next:
            print("More contents available.")
        else:
            print("No more contents.")

    def __str__(self):
        vstr = libacars.lib.la_proto_tree_format_text(None, self.p)
        result = vstr.contents.str.decode("ascii")
        libacars.lib.la_vstring_destroy(vstr, True)
        return result

    def __del__(self):
        libacars.lib.la_proto_tree_destroy(self.p)


if __name__ == '__main__':
    import sys

    print(f"LibACARS version: {libacars.version}\n")

    if len(sys.argv) <= 1:
        print("No arguments provided.", file=sys.stderr)
        sys.exit(1)

    for i, arg in enumerate(sys.argv[1:], start=1):
        data = bytes.fromhex(arg)
        obj = libacars(data, la_msg_dir.LA_MSG_DIR_UNKNOWN, time=i if len(sys.argv) > 2 else None)
        if obj.is_err():
            print(f"Error parsing input #{i}")
            continue
        if not obj.is_reasm():
            print(f"Input #{i}:", obj)
            print("JSON:")
            print(obj.json())

    print("Processing complete.")