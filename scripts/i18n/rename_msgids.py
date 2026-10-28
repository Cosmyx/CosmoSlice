#!/usr/bin/env python3
"""Rename msgids in place in the pot and every .po, following a frozen old -> new mapping (D-004).

    python3 scripts/i18n/rename_msgids.py [--mapping FILE] [--catalogs DIR] [--check]

For each pair, the entry whose msgid is `old` gets msgid `new`, laid out the gettext way. In a .po, an entry with a
non-empty translation is also marked `fuzzy` and gets `#| msgid "<old>"`, preceded by `#| msgctxt` when it has a
context (unless it already carries a previous msgid), so translators see exactly what changed. Every other byte of
every file is left as it is: no re-wrapping, no reordering, no header change, LF kept.

Every catalogue is computed before any is written, so a failure leaves no file half-renamed.

The tool is idempotent: a pair whose `new` msgid is present and whose `old` is gone is already applied. It fails
when, in any catalogue, neither the old nor the new msgid exists, or when both exist (the rename would create a
duplicate). With --check it writes nothing and exits 1 when a file would change.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import po

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPPING = REPO_ROOT / "scripts" / "i18n" / "data" / "cosmoslice_rename.json"
DEFAULT_CATALOGS = REPO_ROOT / "localization" / "i18n"


class RenameError(Exception):
    """The mapping or a catalogue does not allow a safe rename."""


@dataclass(frozen=True)
class Pair:
    old: str
    new: str


@dataclass
class Result:
    text: str
    renamed: int = 0
    fuzzied: int = 0


def load_mapping_data(raw: object) -> list[Pair]:
    """Validate a decoded mapping: a list of {old, new}, no identity, no duplicate, no chain."""
    if not isinstance(raw, list):
        raise RenameError("mapping must be a JSON list of {old, new} objects")
    pairs: list[Pair] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("old"), str) or not isinstance(item.get("new"), str):
            raise RenameError(f"mapping item needs string old and new: {item!r}")
        if item["old"] == item["new"]:
            raise RenameError(f"mapping item with identical old and new: {item['old']!r}")
        pairs.append(Pair(item["old"], item["new"]))
    olds = [p.old for p in pairs]
    news = [p.new for p in pairs]
    for label, values in (("old", olds), ("new", news)):
        seen: set[str] = set()
        for value in values:
            if value in seen:
                raise RenameError(f"duplicate {label} msgid in mapping: {value!r}")
            seen.add(value)
    chained = set(olds) & set(news)
    if chained:
        raise RenameError(f"mapping chain (a new msgid is also an old one): {sorted(chained)!r}")
    return pairs


def load_mapping(path: Path) -> list[Pair]:
    return load_mapping_data(json.loads(path.read_text(encoding="utf-8")))


def _edit_entry(lines: list[str], entry: po.Entry, new: str) -> tuple[int, int, list[str], bool]:
    """Return (start, end, replacement lines, fuzzied) for the comment+field block of one entry."""
    msgid = entry.get("msgid")
    first_field = entry.fields[0].start
    block = list(lines[entry.start : msgid.end])
    rel_msgid = msgid.start - entry.start
    new_block = block[:rel_msgid] + po.render_field("msgid", new)
    fuzzied = False
    if entry.translated:
        has_previous = any(line.startswith("#|") for _, line in entry.comments)
        if not has_previous:
            insert_at = first_field - entry.start
            previous_lines = po.render_field("msgid", entry.msgid, prefix="#| ")
            if entry.msgctxt is not None:
                # gettext order: the previous context comes before the previous msgid.
                previous_lines = po.render_field("msgctxt", entry.msgctxt, prefix="#| ") + previous_lines
            new_block[insert_at:insert_at] = previous_lines
        if not entry.is_fuzzy:
            flag_index = next((n - entry.start for n, line in entry.comments if line.startswith("#,")), None)
            if flag_index is not None:
                rest = new_block[flag_index][2:].strip()
                new_block[flag_index] = f"#, fuzzy, {rest}" if rest else "#, fuzzy"
            else:
                previous = next((n - entry.start for n, line in entry.comments if line.startswith("#|")), None)
                insert_at = previous if previous is not None else first_field - entry.start
                new_block.insert(insert_at, "#, fuzzy")
            fuzzied = True
    return entry.start, msgid.end, new_block, fuzzied


def rename_text(text: str, pairs: list[Pair]) -> Result:
    """Apply every pair to one catalogue's text and return the new text and counts."""
    lines, entries = po.parse(text)
    active = po.active_entries(entries)
    by_msgid: dict[str, list[po.Entry]] = {}
    for entry in active:
        by_msgid.setdefault(entry.msgid, []).append(entry)

    edits: list[tuple[int, int, list[str], bool]] = []
    for pair in pairs:
        olds = by_msgid.get(pair.old, [])
        news = by_msgid.get(pair.new, [])
        if not olds and not news:
            raise RenameError(f"neither old nor new msgid present: {pair.old!r}")
        if olds and news:
            old_ctx = {e.msgctxt for e in olds}
            if old_ctx & {e.msgctxt for e in news}:
                raise RenameError(f"new msgid already exists next to the old one: {pair.new!r}")
        edits += [_edit_entry(lines, entry, pair.new) for entry in olds]

    result = Result(text=text)
    for start, end, replacement, fuzzied in sorted(edits, key=lambda e: e[0], reverse=True):
        lines[start:end] = replacement
        result.renamed += 1
        result.fuzzied += int(fuzzied)
    result.text = "\n".join(lines)
    return result


def discover_catalogs(root: Path) -> list[Path]:
    """The pot files at the root of the catalogue folder, then every <lang>/*.po, in a stable order."""
    pots = sorted(root.glob("*.pot"))
    pos = sorted(root.glob("*/*.po"), key=lambda p: p.relative_to(root).as_posix())
    return pots + pos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="JSON list of {old, new}")
    parser.add_argument("--catalogs", type=Path, default=DEFAULT_CATALOGS, help="folder with the pot and <lang>/")
    parser.add_argument("--check", action="store_true", help="write nothing, exit 1 if a file would change")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        pairs = load_mapping(args.mapping)
        # Compute every catalogue first, write only once all succeeded: a failure leaves no file half-renamed.
        changed: list[tuple[Path, Result]] = []
        for path in discover_catalogs(args.catalogs):
            text = path.read_bytes().decode("utf-8")
            try:
                result = rename_text(text, pairs)
            except RenameError as exc:
                raise RenameError(f"{path}: {exc}") from exc
            if result.text != text:
                changed.append((path, result))
    except RenameError as exc:
        print(f"rename_msgids: {exc}", file=sys.stderr)
        return 2
    for path, result in changed:
        print(f"{path.relative_to(args.catalogs).as_posix()}: {result.renamed} renamed, {result.fuzzied} fuzzy")
        if not args.check:
            path.write_bytes(result.text.encode("utf-8"))
    if args.check and changed:
        print(f"rename_msgids: {len(changed)} catalogue(s) not renamed yet", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
