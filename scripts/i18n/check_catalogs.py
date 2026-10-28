#!/usr/bin/env python3
"""Check every gettext catalogue: msgfmt --check-format passes and no msgid is duplicated.

    python3 scripts/i18n/check_catalogs.py [--catalogs DIR]

Exits 1 and lists the problems when a catalogue fails. msgfmt (GNU gettext) is required: without it the check fails,
it never passes silently.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import po
from rename_msgids import DEFAULT_CATALOGS, discover_catalogs


def msgfmt_problems(path: Path, msgfmt: str) -> list[str]:
    """Problems reported by `msgfmt --check-format` for one catalogue (empty when it passes)."""
    result = subprocess.run(
        [msgfmt, "--check-format", "-o", os.devnull, str(path)], capture_output=True, text=True, check=False
    )
    if result.returncode == 0 and not result.stderr.strip():
        return []
    return [line for line in (result.stderr or result.stdout).splitlines() if line.strip()] or ["msgfmt failed"]


def duplicate_msgids(text: str) -> list[str]:
    """msgids (with their context) that appear more than once among the active entries."""
    _, entries = po.parse(text)
    seen: set[tuple[str | None, str]] = set()
    duplicates: list[str] = []
    for entry in po.active_entries(entries):
        key = (entry.msgctxt, entry.msgid)
        if key in seen:
            duplicates.append(entry.msgid)
        seen.add(key)
    return duplicates


def check(catalogs: Path, msgfmt: str | None = None) -> list[str]:
    """Every problem of every catalogue below `catalogs`, as printable lines."""
    msgfmt = msgfmt or shutil.which("msgfmt")
    if not msgfmt:
        return ["msgfmt not found: install GNU gettext (it is in the CI image, use `just i18n-check`)"]
    problems: list[str] = []
    for path in discover_catalogs(catalogs):
        rel = path.relative_to(catalogs).as_posix()
        if path.suffix == ".po":
            problems += [f"{rel}: {line}" for line in msgfmt_problems(path, msgfmt)]
        problems += [
            f"{rel}: duplicate msgid {msgid!r}" for msgid in duplicate_msgids(path.read_text(encoding="utf-8"))
        ]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogs", type=Path, default=DEFAULT_CATALOGS, help="folder with the pot and <lang>/")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    problems = check(args.catalogs)
    for problem in problems:
        print(problem)
    print(f"check_catalogs: {len(discover_catalogs(args.catalogs))} catalogues, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
