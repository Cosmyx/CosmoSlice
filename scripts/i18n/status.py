#!/usr/bin/env python3
"""Report what a translator still has to do after the CosmoSlice rename, for one language or all.

    python3 scripts/i18n/status.py [lang]

For each language: the renamed entries still fuzzy (fix the translation, then drop `fuzzy` and the `#|` line), the
translated entries whose msgstr still names the upstream product (review: keep only when the source keeps it too),
and the setup-guide text.js keys of its block that still name the upstream product.
"""

from __future__ import annotations

import sys
from pathlib import Path

import po
import product_name as pn
from rename_msgids import DEFAULT_CATALOGS


def language_status(path: Path, renamed: set[str], kept: set[str]) -> dict[str, list[str]]:
    """Fuzzy renamed msgids and stray msgstrs of one .po file."""
    lang = path.parent.name
    _, entries = po.parse(path.read_text(encoding="utf-8"))
    fuzzy: list[str] = []
    stray: list[str] = []
    for entry in po.active_entries(entries):
        if entry.msgid in renamed and entry.is_fuzzy:
            fuzzy.append(entry.msgid)
            continue
        if entry.is_fuzzy or not entry.translated or entry.msgid in kept:
            continue
        if any(pn.has_token(s) or pn.has_native_token(s, lang) for s in entry.msgstrs):
            stray.append(entry.msgid)
    return {"fuzzy": fuzzy, "stray": stray}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    wanted = args[0] if args else ""
    renamed = {pair["new"] for pair in pn.load_mapping()}
    kept = {item["msgid"] for item in pn.load_allowlist()["msgids"]}
    files = sorted(DEFAULT_CATALOGS.glob("*/*.po"), key=lambda p: p.parent.name)
    if wanted:
        files = [p for p in files if p.parent.name == wanted]
        if not files:
            print(f"status: no catalogue for language '{wanted}'", file=sys.stderr)
            return 2
    stale_keys = pn.stale_text_js_keys()
    for path in files:
        lang = path.parent.name
        status = language_status(path, renamed, kept)
        pending = stale_keys.get(lang, [])
        print(f"{lang}: {len(status['fuzzy'])} fuzzy renamed, {len(status['stray'])} stray, {len(pending)} text.js")
        if wanted:
            for label in ("fuzzy", "stray"):
                for msgid in status[label]:
                    print(f"  {label}: {msgid!r}")
            for key in pending:
                print(f"  text.js: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
