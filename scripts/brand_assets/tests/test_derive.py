"""derive.py logic with a fake renderer: write only on change, check lists stale outputs, stable compares runs."""

import os
import struct
import zlib
from pathlib import Path

import derive
import icns
import pytest


def fake_png(size: int, salt: bytes = b"") -> bytes:
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    chunk = b"IHDR" + ihdr
    head = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + chunk + struct.pack(">I", zlib.crc32(chunk))
    return head + salt


def fake_renderer(source: Path, size: int) -> bytes:
    return fake_png(size, source.read_bytes())


def setup_tree(tmp_path: Path) -> tuple[Path, list[derive.Entry]]:
    (tmp_path / "logo.svg").write_text("<svg/>", encoding="utf-8")
    entries = [
        derive.Entry("logo.svg", "out/logo.png", "png", 154),
        derive.Entry("logo.svg", "out/app.icns", "icns", None),
    ]
    (tmp_path / "out").mkdir()
    return tmp_path, entries


def test_render_png_entry(tmp_path):
    root, entries = setup_tree(tmp_path)
    assert derive.render_entry(entries[0], root, fake_renderer) == fake_png(154, b"<svg/>")


def test_render_icns_entry_holds_every_size(tmp_path):
    root, entries = setup_tree(tmp_path)
    data = derive.render_entry(entries[1], root, fake_renderer)
    payloads = dict(icns.parse_icns(data))
    assert payloads["ic10"] == fake_png(1024, b"<svg/>")
    assert payloads["icp4"] == fake_png(16, b"<svg/>")


def test_write_creates_then_leaves_unchanged_files_alone(tmp_path):
    root, entries = setup_tree(tmp_path)
    assert derive.write(entries, root, fake_renderer) == ["out/logo.png", "out/app.icns"]
    logo = root / "out" / "logo.png"
    os.utime(logo, (1, 1))
    assert derive.write(entries, root, fake_renderer) == []
    assert logo.stat().st_mtime == 1


def test_write_rewrites_stale_file_in_place(tmp_path):
    root, entries = setup_tree(tmp_path)
    logo = root / "out" / "logo.png"
    logo.write_bytes(b"old orca bytes")
    assert derive.write(entries[:1], root, fake_renderer) == ["out/logo.png"]
    assert logo.read_bytes() == fake_png(154, b"<svg/>")


def test_check_lists_stale_and_missing_outputs(tmp_path):
    root, entries = setup_tree(tmp_path)
    (root / "out" / "logo.png").write_bytes(b"old")
    assert derive.check(entries, root, fake_renderer) == ["out/logo.png", "out/app.icns"]
    derive.write(entries, root, fake_renderer)
    assert derive.check(entries, root, fake_renderer) == []


def test_stable_reports_differing_runs(tmp_path):
    root, entries = setup_tree(tmp_path)
    assert derive.stable(entries, root, fake_renderer) == []
    calls = iter(range(10_000))

    def flaky(source: Path, size: int) -> bytes:
        return fake_png(size, str(next(calls)).encode())

    assert derive.stable(entries, root, flaky) == ["out/logo.png", "out/app.icns"]


def test_missing_resvg_fails_with_a_hint(monkeypatch):
    monkeypatch.setattr(derive.shutil, "which", lambda name: None)
    with pytest.raises(derive.ResvgMissingError, match="just"):
        derive.find_resvg()


def test_resvg_renders_a_square_png(tmp_path):
    """Needs the pinned resvg: fails (never skips) outside the CI image, see find_resvg's hint."""
    source = tmp_path / "square.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="#123"/></svg>',
        encoding="utf-8",
    )
    render = derive.resvg_renderer()
    data = render(source, 48)
    assert icns.png_size(data) == (48, 48)
    assert render(source, 48) == data
