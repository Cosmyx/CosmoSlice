"""Minimal, deterministic Apple ICNS writer and structural parser.

The writer emits one fixed set of PNG-payload entries, always in the same order, with no table of contents, no
info chunk and no timestamp, so the same PNG payloads always give the same bytes on every host.
"""

from __future__ import annotations

import struct
from collections.abc import Mapping

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
HEADER = struct.Struct(">4sI")

# (OSType, pixel size) in file order. ic11..ic14 are the @2x variants (32@2x is 64 px, etc.), payload size given.
ENTRIES: tuple[tuple[str, int], ...] = (
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
    ("ic11", 32),
    ("ic12", 64),
    ("ic13", 256),
    ("ic14", 512),
)
REQUIRED_SIZES: tuple[int, ...] = tuple(sorted({size for _, size in ENTRIES}))


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) read from a PNG's IHDR chunk; ValueError when the bytes are not a PNG."""
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise ValueError("payload is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def write_icns(pngs: Mapping[int, bytes]) -> bytes:
    """ICNS bytes from square PNG payloads keyed by pixel size; every size of REQUIRED_SIZES, and only those."""
    unsupported = sorted(set(pngs) - set(REQUIRED_SIZES))
    if unsupported:
        raise ValueError(f"unsupported icon sizes: {unsupported}")
    missing = sorted(set(REQUIRED_SIZES) - set(pngs))
    if missing:
        raise ValueError(f"missing icon sizes: {missing}")
    for size in REQUIRED_SIZES:
        try:
            dims = png_size(pngs[size])
        except ValueError as error:
            raise ValueError(f"{size} px payload is not a PNG") from error
        if dims != (size, size):
            raise ValueError(f"{size} px payload is {dims[0]}x{dims[1]}")
    body = b"".join(
        HEADER.pack(kind.encode("ascii"), HEADER.size + len(pngs[size])) + pngs[size] for kind, size in ENTRIES
    )
    return HEADER.pack(b"icns", HEADER.size + len(body)) + body


def parse_icns(data: bytes) -> list[tuple[str, bytes]]:
    """Chunks of an ICNS file as (OSType, payload); ValueError when the structure is broken.

    Only the container is checked (magic, total length, chunk bounds), so files written by other tools are valid too.
    """
    if len(data) < HEADER.size:
        raise ValueError("too short for an ICNS header")
    magic, total = HEADER.unpack_from(data, 0)
    if magic != b"icns":
        raise ValueError("missing 'icns' magic")
    if total != len(data):
        raise ValueError(f"header length {total} != file size {len(data)}")
    chunks: list[tuple[str, bytes]] = []
    offset = HEADER.size
    while offset < total:
        if total - offset < HEADER.size:
            raise ValueError(f"truncated chunk header at offset {offset}")
        kind, length = HEADER.unpack_from(data, offset)
        if length < HEADER.size or offset + length > total:
            raise ValueError(f"chunk {kind!r} at offset {offset} has bad length {length}")
        chunks.append((kind.decode("latin-1"), data[offset + HEADER.size : offset + length]))
        offset += length
    return chunks


def is_valid_icns(data: bytes) -> bool:
    """True when parse_icns accepts the bytes."""
    try:
        parse_icns(data)
    except ValueError:
        return False
    return True
