#!/usr/bin/env python3
"""Derive brand assets (PNG, ICNS) from their SVG source, as listed in derived-assets.toml.

    python3 scripts/brand_assets/derive.py write    # re-render, rewrite only outputs whose bytes changed
    python3 scripts/brand_assets/derive.py check    # exit 1 and list outputs that differ from a fresh render
    python3 scripts/brand_assets/derive.py stable   # render everything twice, exit 1 if the runs differ

Rendering uses `resvg`, which is only present in the pinned CI image: run it through the module justfile
(`just -f scripts/brand_assets/justfile derive|check|stable`), never with a host resvg. See D-010 and D-011.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

if __package__:
    # Imported as the `brand_assets` package (tests): no bare module name lands in sys.modules.
    from . import icns
else:
    # Run as a script: the module folder is sys.path[0].
    import icns

MODULE_DIR = Path(__file__).resolve().parent
MANIFEST = MODULE_DIR / "derived-assets.toml"
REPO_ROOT = MODULE_DIR.parents[1]
FORMATS = ("png", "icns")
KEYS = {"source", "output", "format", "size"}

Renderer = Callable[[Path, int], bytes]


class ResvgMissingError(RuntimeError):
    """resvg is not on PATH: the command was run outside the CI image."""


class RenderError(RuntimeError):
    """resvg failed on a source; the message carries the source path and resvg's stderr."""


@dataclass(frozen=True)
class Entry:
    source: str
    output: str
    format: str
    size: int | None


def _relative_posix(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    if "\\" in value:
        raise ValueError(f"{field} '{value}' must use POSIX '/' separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in path.parts[0]:
        raise ValueError(f"{field} '{value}' must be relative to the repository root, without '..'")
    return path.as_posix()


def _entry(raw: object, root: Path) -> Entry:
    if not isinstance(raw, Mapping):
        raise ValueError("must be a table ([[derived]])")
    unknown = sorted(set(raw) - KEYS)
    if unknown:
        raise ValueError(f"unknown keys {unknown}")
    source = _relative_posix(raw.get("source"), "source")
    output = _relative_posix(raw.get("output"), "output")
    if source == output:
        raise ValueError(f"output '{output}' is its own source")
    fmt = raw.get("format")
    if fmt not in FORMATS:
        raise ValueError(f"format {fmt!r} must be one of {FORMATS}")
    size = raw.get("size")
    if fmt == "png" and (not isinstance(size, int) or isinstance(size, bool) or size <= 0):
        raise ValueError(f"png output '{output}' needs a positive integer size")
    if fmt == "icns" and size is not None:
        raise ValueError(f"icns output '{output}' takes no size (it holds every icon size)")
    if not (root / source).is_file():
        raise ValueError(f"source '{source}' does not exist")
    return Entry(source, output, fmt, size if isinstance(size, int) else None)


def load_manifest(manifest: Path = MANIFEST, root: Path = REPO_ROOT) -> list[Entry]:
    """Validated entries of the manifest, in file order."""
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    derived = data.get("derived", [])
    if not isinstance(derived, list):
        raise ValueError(f"{manifest.name}: derived must be an array of tables ([[derived]])")
    entries = []
    for index, raw in enumerate(derived):
        try:
            entries.append(_entry(raw, root))
        except ValueError as error:
            raise ValueError(f"{manifest.name} entry {index + 1}: {error}") from error
    outputs = [entry.output for entry in entries]
    duplicates = sorted({o for o in outputs if outputs.count(o) > 1})
    if duplicates:
        raise ValueError(f"{manifest.name}: duplicate outputs {duplicates}")
    return entries


def find_resvg() -> str:
    path = shutil.which("resvg")
    if path is None:
        raise ResvgMissingError(
            "resvg not found: run through `just -f scripts/brand_assets/justfile <recipe>` or "
            "`just test brand_assets`, which use the pinned CI image"
        )
    return path


def resvg_renderer(command: Sequence[str] | None = None) -> Renderer:
    """Renderer that rasterises an SVG to a square PNG of `size` px with the pinned resvg.

    `command` replaces the resvg invocation (its arguments are appended); RenderError when it fails.
    """
    base = list(command) if command is not None else [find_resvg()]

    def render(source: Path, size: int) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.png"
            try:
                subprocess.run(
                    [*base, "-w", str(size), "-h", str(size), str(source), str(out)],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as error:
                stderr = error.stderr.decode("utf-8", errors="replace").strip() if error.stderr else ""
                raise RenderError(
                    f"resvg failed on {source} at {size} px (exit status {error.returncode}): {stderr or 'no output'}"
                ) from error
            return out.read_bytes()

    return render


def render_entry(entry: Entry, root: Path, render: Renderer) -> bytes:
    """Bytes of one output, freshly rendered from its source."""
    source = root / entry.source
    if entry.format == "png":
        if entry.size is None:
            raise ValueError(f"png output '{entry.output}' has no size")
        return render(source, entry.size)
    return icns.write_icns({size: render(source, size) for size in icns.REQUIRED_SIZES})


def write(entries: Iterable[Entry], root: Path, render: Renderer) -> list[str]:
    """Render every entry; rewrite (in place) only the outputs whose bytes changed. Returns those outputs."""
    changed = []
    for entry in entries:
        data = render_entry(entry, root, render)
        target = root / entry.output
        if target.is_file() and target.read_bytes() == data:
            continue
        # Overwrite in place: the folder is never deleted or recreated (SMB share).
        with target.open("wb") as handle:
            handle.write(data)
        changed.append(entry.output)
    return changed


def check(entries: Iterable[Entry], root: Path, render: Renderer) -> list[str]:
    """Outputs that are missing or differ from a fresh render."""
    stale = []
    for entry in entries:
        target = root / entry.output
        if not target.is_file() or target.read_bytes() != render_entry(entry, root, render):
            stale.append(entry.output)
    return stale


def stable(entries: Iterable[Entry], root: Path, render: Renderer) -> list[str]:
    """Outputs whose two consecutive renders differ."""
    return [e.output for e in entries if render_entry(e, root, render) != render_entry(e, root, render)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("write", "check", "stable"))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        render = resvg_renderer()
    except ResvgMissingError as error:
        print(f"derive.py: {error}", file=sys.stderr)
        return 2
    entries = load_manifest()
    if args.mode == "write":
        for output in write(entries, REPO_ROOT, render):
            print(f"rewrote {output}")
        return 0
    if args.mode == "check":
        stale = check(entries, REPO_ROOT, render)
        for output in stale:
            print(f"stale: {output} (run `just -f scripts/brand_assets/justfile derive`)", file=sys.stderr)
        print(f"derive check: {len(entries)} outputs, {len(stale)} stale")
        return 1 if stale else 0
    unstable = stable(entries, REPO_ROOT, render)
    for output in unstable:
        print(f"unstable: {output} (two renders differ)", file=sys.stderr)
    print(f"derive stable: {len(entries)} outputs rendered twice, {len(unstable)} differ")
    return 1 if unstable else 0


if __name__ == "__main__":
    sys.exit(main())
