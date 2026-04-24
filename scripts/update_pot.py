#!/usr/bin/env python3
"""update_pot.py — Scan the C++ source tree for translatable strings and
append any entries that are missing from OrcaSlicer.pot and (optionally)
every per-language .po file.

Recognised macros (matching the xgettext --keyword flags in run_gettext):
    L("…")   _L("…")   _u8L("…")
    L_CONTEXT("…", "ctx")
    _L_PLURAL("singular", "plural", n)
    _CTX("…", "ctx")   _CTX_utf8("…", "ctx")

Run from the repository root:
    python3 scripts/update_pot.py [options]

Options:
    --src-dir  DIR   Directory tree to scan          [src/]
    --list     FILE  Optional: restrict to files in list.txt instead of all src/
    --pot      FILE  Template to update              [localization/i18n/OrcaSlicer.pot]
    --po-dir   DIR   Parent of per-language dirs     [localization/i18n/]
    --update-po      Also patch every .po file with the new entries
    --dry-run        Print what would change, do not write any file
    -v/--verbose     Print per-file progress
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Entry:
    msgid:        str
    msgid_plural: Optional[str] = None
    msgctxt:      Optional[str] = None

    @property
    def key(self) -> tuple:
        return (self.msgctxt, self.msgid, self.msgid_plural)

    def format_pot(self) -> str:
        """Render as a .pot block (no location comment, empty msgstr)."""
        lines = []
        if self.msgctxt is not None:
            lines.append(f"msgctxt {po_quote(self.msgctxt)}")
        lines.append(f"msgid {po_quote(self.msgid)}")
        if self.msgid_plural is not None:
            lines.append(f"msgid_plural {po_quote(self.msgid_plural)}")
            lines.append('msgstr[0] ""')
            lines.append('msgstr[1] ""')
        else:
            lines.append('msgstr ""')
        return "\n".join(lines)


# ── PO string quoting / unquoting ─────────────────────────────────────────────

def po_quote(s: str) -> str:
    """Encode a Python string as a PO-format double-quoted value.

    Strings containing embedded newlines are written in multi-line PO format:
        ""
        "first line\\n"
        "second line"
    """
    buf = []
    for ch in s:
        if   ch == "\\":  buf.append("\\\\")
        elif ch == '"':   buf.append('\\"')
        elif ch == "\n":  buf.append("\\n")
        elif ch == "\r":  buf.append("\\r")
        elif ch == "\t":  buf.append("\\t")
        else:             buf.append(ch)
    escaped = "".join(buf)

    if "\\n" in escaped:
        parts = escaped.split("\\n")
        lines = ['""']
        for i, part in enumerate(parts):
            suffix = "\\n" if i < len(parts) - 1 else ""
            if part or suffix:
                lines.append(f'"{part}{suffix}"')
        return "\n".join(lines)

    return f'"{escaped}"'


def po_unquote(raw: str) -> str:
    """Decode a PO string value (one or more "…" segments) to a Python str."""
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
    joined = "".join(parts)
    result = []
    i = 0
    while i < len(joined):
        if joined[i] == "\\" and i + 1 < len(joined):
            esc = joined[i + 1]
            if   esc == "n":  result.append("\n"); i += 2
            elif esc == "t":  result.append("\t"); i += 2
            elif esc == "r":  result.append("\r"); i += 2
            elif esc == '"':  result.append('"');  i += 2
            elif esc == "\\":  result.append("\\"); i += 2
            else:
                result.append("\\")
                result.append(esc)
                i += 2
        else:
            result.append(joined[i])
            i += 1
    return "".join(result)


# ── POT / PO parser ───────────────────────────────────────────────────────────

def _parse_block(block: str) -> Optional[tuple]:
    """Parse one PO entry block and return (msgctxt, msgid, msgid_plural).

    Returns None for the header block (msgid "") or empty/comment-only blocks.
    """
    ctx = mid = plural = None
    cur_field: Optional[str] = None
    cur_lines: list[str] = []

    def flush() -> None:
        nonlocal ctx, mid, plural, cur_field, cur_lines
        if cur_field and cur_lines:
            val = po_unquote(" ".join(cur_lines))
            if   cur_field == "msgctxt":       ctx    = val
            elif cur_field == "msgid":         mid    = val
            elif cur_field == "msgid_plural":  plural = val
        cur_field = None
        cur_lines = []

    for line in block.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("msgctxt "):
            flush(); cur_field = "msgctxt";      cur_lines = [s[8:]]
        elif s.startswith("msgid_plural "):
            flush(); cur_field = "msgid_plural"; cur_lines = [s[13:]]
        elif s.startswith("msgid "):
            flush(); cur_field = "msgid";        cur_lines = [s[6:]]
        elif s.startswith("msgstr"):
            flush()  # stop collecting; rest of block is the translation
        elif s.startswith('"') and cur_field:
            cur_lines.append(s)

    flush()
    return (ctx, mid, plural) if (mid is not None and mid != "") else None


def parse_keys(path: Path) -> set[tuple]:
    """Return a set of (msgctxt, msgid, msgid_plural) tuples from a PO/POT file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"WARNING: cannot read {path}: {exc}", file=sys.stderr)
        return set()

    keys: set[tuple] = set()
    for block in re.split(r"\n[ \t]*\n", text):
        entry = _parse_block(block)
        if entry:
            keys.add(entry)
    return keys


# ── C++ source scanner ────────────────────────────────────────────────────────

# Matches and removes C/C++ line and block comments while leaving string
# literals intact.
_COMMENT_RE = re.compile(
    r'("(?:[^"\\]|\\.)*")'   # group 1 – keep: string literal
    r"|(/\*.*?\*/)"           # group 2 – drop: block comment
    r"|(//[^\n]*)",           # group 3 – drop: line comment
    re.DOTALL,
)


def strip_cpp_comments(src: str) -> str:
    return _COMMENT_RE.sub(lambda m: m.group(1) or " ", src)


# A single C string literal, then a sequence of one-or-more adjacent ones.
_STR_LIT = r'"(?:[^"\\]|\\.)*"'
_STR_SEQ = rf"(?:{_STR_LIT}\s*)+"


def join_cstrings(raw: str) -> str:
    """Join adjacent C string literals and decode escape sequences."""
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
    joined = "".join(parts)
    result = []
    i = 0
    while i < len(joined):
        if joined[i] == "\\" and i + 1 < len(joined):
            esc = joined[i + 1]
            if   esc == "n":  result.append("\n"); i += 2
            elif esc == "t":  result.append("\t"); i += 2
            elif esc == "r":  result.append("\r"); i += 2
            elif esc == '"':  result.append('"');  i += 2
            elif esc == "\\":  result.append("\\"); i += 2
            else:
                result.append("\\")
                result.append(esc)
                i += 2
        else:
            result.append(joined[i])
            i += 1
    return "".join(result)


# ── Macro regex patterns ──────────────────────────────────────────────────────
# Negative lookbehind (?<![_A-Za-z0-9]) prevents matching e.g. someVar_L(…).

# L("…")  _L("…")  _u8L("…")
_RE_SIMPLE = re.compile(
    rf"(?<![_A-Za-z0-9])(?:_u8L|_L|L)\s*\(\s*({_STR_SEQ})\s*\)",
    re.DOTALL,
)

# _L_PLURAL("singular", "plural", n)
_RE_PLURAL = re.compile(
    rf"(?<![_A-Za-z0-9])_L_PLURAL\s*\(\s*({_STR_SEQ})\s*,\s*({_STR_SEQ})\s*,",
    re.DOTALL,
)

# L_CONTEXT("…", "ctx")  _CTX("…", "ctx")  _CTX_utf8("…", "ctx")
_RE_CTX = re.compile(
    rf"(?<![_A-Za-z0-9])(?:L_CONTEXT|_CTX_utf8|_CTX)\s*\(\s*({_STR_SEQ})\s*,\s*({_STR_SEQ})\s*\)",
    re.DOTALL,
)


def extract_from_file(path: Path) -> list[Entry]:
    """Return all translatable string entries found in *path*."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    src = strip_cpp_comments(src)

    seen: set[tuple] = set()
    result: list[Entry] = []

    def add(e: Entry) -> None:
        if e.key not in seen:
            seen.add(e.key)
            result.append(e)

    for m in _RE_SIMPLE.finditer(src):
        text = join_cstrings(m.group(1))
        if text:
            add(Entry(msgid=text))

    for m in _RE_PLURAL.finditer(src):
        sing = join_cstrings(m.group(1))
        plur = join_cstrings(m.group(2))
        if sing:
            add(Entry(msgid=sing, msgid_plural=plur or None))

    for m in _RE_CTX.finditer(src):
        text = join_cstrings(m.group(1))
        ctx  = join_cstrings(m.group(2))
        if text:
            add(Entry(msgid=text, msgctxt=ctx or None))

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

SOURCE_EXTENSIONS = {".cpp", ".hpp", ".h", ".mm", ".cxx", ".cc"}


def collect_source_files(src_dir: Path, list_file: Optional[Path]) -> list[Path]:
    """Return the list of source files to scan.

    If *list_file* is given, restrict to paths listed in that file (relative
    to the repository root).  Otherwise scan *src_dir* recursively.
    """
    if list_file is not None:
        root = Path(".")
        paths = []
        try:
            for line in list_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    p = root / line
                    if p.suffix in SOURCE_EXTENSIONS and p.exists():
                        paths.append(p)
        except OSError as exc:
            sys.exit(f"ERROR: cannot read list file {list_file}: {exc}")
        return paths

    return sorted(
        p for p in src_dir.rglob("*") if p.suffix in SOURCE_EXTENSIONS
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Add missing translatable strings to .pot / .po files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--src-dir", default="src",
        help="Source directory to scan recursively (default: src/)",
    )
    ap.add_argument(
        "--list", dest="list_file", default=None,
        help="Restrict scan to files listed in this file (e.g. localization/i18n/list.txt)",
    )
    ap.add_argument(
        "--pot", default="localization/i18n/OrcaSlicer.pot",
        help="Path to the .pot template file",
    )
    ap.add_argument(
        "--po-dir", default="localization/i18n",
        help="Parent directory containing per-language subdirs",
    )
    ap.add_argument(
        "--update-po", action="store_true",
        help="Also append missing entries to every .po file",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be added without writing any file",
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print per-file progress",
    )
    args = ap.parse_args()

    src_dir   = Path(args.src_dir)
    pot_path  = Path(args.pot)
    po_dir    = Path(args.po_dir)
    list_file = Path(args.list_file) if args.list_file else None

    if not src_dir.exists() and list_file is None:
        sys.exit(f"ERROR: source directory not found: {src_dir}")
    if not pot_path.exists():
        sys.exit(f"ERROR: .pot file not found: {pot_path}")

    # ── 1. Collect source files ───────────────────────────────────────────────
    src_files = collect_source_files(src_dir, list_file)
    source_label = str(list_file) if list_file else f"{src_dir}/"
    print(f"Scanning {len(src_files)} source files ({source_label})")

    # ── 2. Extract all translatable strings ──────────────────────────────────
    all_entries: dict[tuple, Entry] = {}
    for fpath in src_files:
        entries = extract_from_file(fpath)
        for e in entries:
            if e.key not in all_entries:
                all_entries[e.key] = e
        if args.verbose and entries:
            print(f"  {fpath}: {len(entries)} strings")

    print(f"Unique translatable strings found: {len(all_entries)}")

    # ── 3. Compare against existing .pot ─────────────────────────────────────
    existing = parse_keys(pot_path)
    print(f"Existing entries in .pot:          {len(existing)}")

    missing: dict[tuple, Entry] = {
        k: v for k, v in all_entries.items() if k not in existing
    }
    print(f"Missing entries to add:            {len(missing)}")

    if not missing:
        print("\nEverything is up to date.")
        return

    new_blocks = "\n\n".join(e.format_pot() for e in missing.values())

    # ── 4. Update .pot ────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n--- Dry-run: would append to .pot ---")
        print(new_blocks)
    else:
        original = pot_path.read_text(encoding="utf-8")
        pot_path.write_text(
            original.rstrip() + "\n\n" + new_blocks + "\n",
            encoding="utf-8",
        )
        print(f"\nUpdated {pot_path}  (+{len(missing)} entries)")

    # ── 5. Update .po files (optional) ───────────────────────────────────────
    if args.update_po:
        po_files = sorted(po_dir.rglob("OrcaSlicer_*.po"))
        if not po_files:
            print(f"No .po files found under {po_dir}")
            return
        print(f"\nUpdating {len(po_files)} .po files...")
        total_added = 0
        for po_path in po_files:
            po_existing = parse_keys(po_path)
            po_missing  = {k: v for k, v in missing.items() if k not in po_existing}
            if not po_missing:
                if args.verbose:
                    print(f"  {po_path.name}: already up to date")
                continue
            po_blocks = "\n\n".join(e.format_pot() for e in po_missing.values())
            if args.dry_run:
                print(f"  {po_path.name}: would add {len(po_missing)} entries")
                if args.verbose:
                    print(po_blocks)
            else:
                original = po_path.read_text(encoding="utf-8")
                po_path.write_text(
                    original.rstrip() + "\n\n" + po_blocks + "\n",
                    encoding="utf-8",
                )
                print(f"  {po_path.name}: +{len(po_missing)} entries")
            total_added += len(po_missing)
        if not args.dry_run:
            print(f"Total .po additions: {total_added}")


if __name__ == "__main__":
    main()
