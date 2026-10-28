#!/usr/bin/env python3
"""Fail when a tracked text file has CRLF line endings in the working tree (D-008).

    python3 tools/repo/line_endings.py

Only the files git tracks are checked, so local untracked or ignored files (build output, notes, caches) never
fail the gate. It needs git, so it runs on the host as the `check` recipe of tools/repo/justfile: the CI image
has no git, and a worktree's git folder lies outside the mounted repository.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Binary types declared in .gitattributes; they are never checked for line endings.
BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns", ".3mf", ".stl", ".ttf", ".xlsx", ".dll", ".lib", ".exe"}
)
# Bytes sniffed for a NUL to recognise binary content with an unusual suffix.
SNIFF_SIZE = 8000


def parse_ls_files(output: bytes) -> list[str]:
    """Split the output of `git ls-files -z` into repository-relative POSIX paths."""
    return [part.decode("utf-8") for part in output.split(b"\0") if part]


def text_candidates(paths: Iterable[str]) -> list[str]:
    """Drop the paths whose suffix is declared binary."""
    return [p for p in paths if Path(p).suffix.lower() not in BINARY_SUFFIXES]


def crlf_offenders(root: Path, paths: Iterable[str]) -> list[str]:
    """Paths (relative to root) of the text files that contain CRLF; missing files and binary content are skipped."""
    offenders = []
    for rel in paths:
        path = root.joinpath(*rel.split("/"))
        if not path.is_file():
            continue  # tracked but deleted in the working tree
        data = path.read_bytes()
        if b"\0" in data[:SNIFF_SIZE]:
            continue
        if b"\r\n" in data:
            offenders.append(rel)
    return offenders


def tracked_files(root: Path) -> list[str]:
    """Every path git tracks in the working tree at root."""
    output = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    return parse_ls_files(output)


def main(root: Path = REPO_ROOT) -> int:
    try:
        paths = tracked_files(root)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"line_endings: cannot list the tracked files with git: {exc}", file=sys.stderr)
        return 2
    offenders = crlf_offenders(root, text_candidates(paths))
    if offenders:
        print(f"line_endings: CRLF line endings in {len(offenders)} tracked file(s):", file=sys.stderr)
        for rel in offenders:
            print(f"  {rel}", file=sys.stderr)
        return 1
    print(f"line_endings: {len(paths)} tracked files, all LF")
    return 0


if __name__ == "__main__":
    sys.exit(main())
