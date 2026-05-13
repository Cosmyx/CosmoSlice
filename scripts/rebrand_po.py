#!/usr/bin/env python3
"""Replace OrcaSlicer/Orca Slicer/Orca-Slicer with CosmoSlice in msgstr blocks only."""

import argparse
import pathlib
import re
import sys

REPLACEMENTS = [
    ("Orca Slicer", "CosmoSlice"),
    ("Orca-Slicer", "CosmoSlice"),
    ("OrcaSlicer",  "CosmoSlice"),
]

RE_MSGSTR = re.compile(r"^msgstr(?:\[\d+\])?")
RE_MSGID  = re.compile(r"^msgid(?:_plural)?")


def apply_replacements(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def process_file(path: pathlib.Path, dry_run: bool) -> int:
    raw = path.read_bytes()
    crlf = b"\r\n" in raw
    content = raw.decode("utf-8")
    lines = content.splitlines(keepends=True)

    in_msgstr = False
    changed = 0
    out = []

    for line in lines:
        stripped = line.rstrip("\r\n")

        if RE_MSGID.match(stripped):
            in_msgstr = False
        elif RE_MSGSTR.match(stripped):
            in_msgstr = True
        elif not stripped:
            in_msgstr = False

        if in_msgstr:
            new_line = apply_replacements(line)
            if new_line != line:
                changed += 1
                line = new_line

        out.append(line)

    if changed and not dry_run:
        result = "".join(out)
        if crlf:
            result = result.replace("\r\n", "\n").replace("\n", "\r\n")
        path.write_bytes(result.encode("utf-8"))

    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="localization/i18n",
                        help="Root directory to scan (default: localization/i18n)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without writing")
    args = parser.parse_args()

    root = pathlib.Path(args.dir)
    if not root.exists():
        sys.exit(f"Directory not found: {root}")

    files = list(root.rglob("*.po")) + list(root.rglob("*.pot"))
    if not files:
        sys.exit(f"No .po/.pot files found in {root}")

    total = 0
    for f in sorted(files):
        n = process_file(f, args.dry_run)
        if n:
            tag = "[dry-run] " if args.dry_run else ""
            print(f"{tag}{f}  ({n} line{'s' if n != 1 else ''} changed)")
            total += n

    if total == 0:
        print("Nothing to replace.")
    else:
        action = "would change" if args.dry_run else "changed"
        print(f"\nTotal: {total} line{'s' if total != 1 else ''} {action} across {len(files)} files.")


if __name__ == "__main__":
    main()
