"""ICNS writer and parser: layout, PNG payloads, round-trip and rejections."""

import struct
import zlib

import pytest
from brand_assets import icns

EXPECTED_ORDER = [
    ("icp4", 16),
    ("icp5", 32),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
    ("ic11", 32),
    ("ic12", 64),
    ("ic13", 256),
    ("ic14", 512),
]


def make_png(width: int, height: int | None = None) -> bytes:
    """Smallest valid PNG header for the given size (IHDR only, enough for the writer's checks)."""
    height = width if height is None else height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    chunk = b"IHDR" + ihdr
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + chunk + struct.pack(">I", zlib.crc32(chunk))


def all_pngs() -> dict[int, bytes]:
    return {size: make_png(size) for size in icns.REQUIRED_SIZES}


def test_entry_table_is_fixed():
    assert list(icns.ENTRIES) == EXPECTED_ORDER
    assert icns.REQUIRED_SIZES == (16, 32, 64, 128, 256, 512, 1024)


# Pixel size of every OSType slot written, as macOS iconutil reads it (iconutil -c iconset names each slot's file).
APPLE_SLOT_SIZES = {
    "icp4": 16,
    "icp5": 32,
    "ic07": 128,
    "ic08": 256,
    "ic09": 512,
    "ic10": 1024,
    "ic11": 32,
    "ic12": 64,
    "ic13": 256,
    "ic14": 512,
}


def test_entry_sizes_match_apple_slots():
    assert dict(icns.ENTRIES) == APPLE_SLOT_SIZES


def test_icp6_is_never_written():
    # icp6 is a 48 px slot: iconutil rescales whatever it holds to icon_48x48.png.
    assert "icp6" not in dict(icns.ENTRIES)
    kinds = [kind for kind, _ in icns.parse_icns(icns.write_icns(all_pngs()))]
    assert "icp6" not in kinds


def test_header_magic_and_length():
    data = icns.write_icns(all_pngs())
    assert data[:4] == b"icns"
    assert struct.unpack(">I", data[4:8])[0] == len(data)


def test_entries_in_fixed_order_with_png_payloads():
    pngs = all_pngs()
    data = icns.write_icns(pngs)
    entries = icns.parse_icns(data)
    assert [kind for kind, _ in entries] == [kind for kind, _ in EXPECTED_ORDER]
    for (kind, payload), (_, size) in zip(entries, EXPECTED_ORDER, strict=True):
        assert payload == pngs[size], kind
        assert payload.startswith(icns.PNG_SIGNATURE)


def test_no_toc_or_info_chunk():
    kinds = [kind for kind, _ in icns.parse_icns(icns.write_icns(all_pngs()))]
    assert "TOC " not in kinds
    assert "info" not in kinds


def test_output_is_deterministic():
    assert icns.write_icns(all_pngs()) == icns.write_icns(all_pngs())


def test_round_trip_png_size():
    assert icns.png_size(make_png(64, 32)) == (64, 32)


def test_rejects_non_png_payload():
    pngs = all_pngs()
    pngs[128] = b"not a png at all, just bytes"
    with pytest.raises(ValueError, match="not a PNG"):
        icns.write_icns(pngs)


def test_rejects_payload_of_wrong_dimensions():
    pngs = all_pngs()
    pngs[256] = make_png(255)
    with pytest.raises(ValueError, match="256"):
        icns.write_icns(pngs)


def test_rejects_unsupported_size():
    pngs = all_pngs()
    pngs[48] = make_png(48)
    with pytest.raises(ValueError, match="unsupported"):
        icns.write_icns(pngs)


def test_rejects_missing_size():
    pngs = all_pngs()
    del pngs[1024]
    with pytest.raises(ValueError, match="missing"):
        icns.write_icns(pngs)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\x00" * 64,
        b"icns" + struct.pack(">I", 99),
        b"icns" + struct.pack(">I", 16) + b"ic07" + struct.pack(">I", 4),
        b"icns" + struct.pack(">I", 16) + b"ic07" + struct.pack(">I", 40),
    ],
    ids=["empty", "zeros", "length-mismatch", "chunk-too-short", "chunk-overflows"],
)
def test_parser_rejects_malformed_files(data):
    with pytest.raises(ValueError):
        icns.parse_icns(data)
    assert not icns.is_valid_icns(data)


def test_parser_accepts_foreign_chunks():
    """Files written by other tools (TOC, info, legacy RGB chunks) are structurally valid too."""
    body = b"TOC " + struct.pack(">I", 8) + b"it32" + struct.pack(">I", 12) + b"\x00\x00\x00\x00"
    data = b"icns" + struct.pack(">I", 8 + len(body)) + body
    assert icns.is_valid_icns(data)
    assert [kind for kind, _ in icns.parse_icns(data)] == ["TOC ", "it32"]
