#!/usr/bin/env python3
"""
Script to generate I18N translation files for the Cosmyx vendor profile.

This script:
1. Reads i18n_config.json for per-language translation rules
2. Scans all Cosmyx profile JSON files for 'name' fields
3. Applies ordered substitutions to produce translations for each language
4. Writes output to I18N/{lang}.json, grouped by profile type

Config: i18n_config.json (in the same directory)
Output: I18N/*.json (one file per language defined in the config)

Usage:
    python ztool_generate_i18n.py
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "i18n_config.json"
I18N_DIR = BASE_DIR / "I18N"

# ── Scanner config ─────────────────────────────────────────────────────────
EXCLUDE_DIRS = {"I18N", "__pycache__", ".git", "node_modules", ".vscode"}
EXCLUDE_FILES = {"Cosmyx.json", "cosmyx.json"}
VALID_TYPES = {"machine_model", "machine", "process", "filament"}

# Profile type display order in output files
TYPE_ORDER = ["machine_model", "machine", "process", "filament"]


# ── Config loading ─────────────────────────────────────────────────────────

def load_config() -> Dict:
    """Load i18n_config.json."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Profile scanning ───────────────────────────────────────────────────────

def scan_profile_names(base_dir: Path) -> List[Dict]:
    """
    Walk the Cosmyx profile directory and collect every unique profile name.

    Returns a list of {"name": str, "type": str} dicts, in the order they
    are encountered (duplicates removed).
    """
    profiles: List[Dict] = []
    seen: set = set()

    for root, dirs, files in os.walk(base_dir):
        # Prune directories we never want to descend into
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for fname in files:
            if not fname.endswith(".json") or fname in EXCLUDE_FILES:
                continue

            file_path = Path(root) / fname
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            profile_type = data.get("type", "")
            profile_name = data.get("name", "")

            if not profile_name or profile_type not in VALID_TYPES:
                continue

            if profile_name not in seen:
                seen.add(profile_name)
                profiles.append({"name": profile_name, "type": profile_type})

    return profiles


# ── Translation engine ─────────────────────────────────────────────────────

def apply_substitutions(source: str, substitutions: List[List[str]]) -> str:
    """
    Apply an ordered list of [from, to] substitutions to *source*.

    Each substitution replaces all occurrences of *from* with *to*.
    Order matters: put longer / more-specific patterns first
    (e.g. "Extra Fine" before "Fine ").
    """
    result = source
    for from_term, to_term in substitutions:
        result = result.replace(from_term, to_term)
    return result


def generate_entries_for_language(
    profiles: List[Dict],
    lang_config: Dict,
    skip_identity: bool,
) -> Dict[str, List[Dict]]:
    """
    Generate I18N entries for one language, grouped by profile type.

    Returns a dict mapping profile type → list of {source, translation}.
    """
    substitutions: List[List[str]] = lang_config.get("substitutions", [])
    explicit_map: Dict[str, str] = {
        e["source"]: e["translation"]
        for e in lang_config.get("explicit", [])
    }

    # Build grouped output
    grouped: Dict[str, List[Dict]] = {t: [] for t in TYPE_ORDER}
    seen_sources: set = set()

    for profile in profiles:
        source: str = profile["name"]
        ptype: str = profile["type"]

        if source in seen_sources:
            continue

        # Explicit entries override substitutions
        if source in explicit_map:
            translation = explicit_map[source]
        else:
            translation = apply_substitutions(source, substitutions)

        seen_sources.add(source)

        if skip_identity and translation == source:
            continue

        grouped.setdefault(ptype, []).append(
            {"source": source, "translation": translation}
        )

    # Add explicit entries not already covered by profile scan
    for source, translation in explicit_map.items():
        if source not in seen_sources:
            if not skip_identity or translation != source:
                # We don't know the type; put in a fallback bucket
                grouped.setdefault("filament", []).append(
                    {"source": source, "translation": translation}
                )
                seen_sources.add(source)

    return grouped


# ── Output formatting ──────────────────────────────────────────────────────

def _entry_to_json(entry: Dict) -> str:
    """Render a single {source, translation} dict as a compact JSON line."""
    src = json.dumps(entry["source"], ensure_ascii=False)
    trl = json.dumps(entry["translation"], ensure_ascii=False)
    return f'    {{"source": {src}, "translation": {trl}}}'


def render_i18n_json(grouped: Dict[str, List[Dict]]) -> str:
    """
    Render grouped entries as a pretty-printed JSON array with blank lines
    between type groups (matching the existing I18N file style).
    """
    all_lines: List[str] = []

    # Collect non-empty groups in display order
    non_empty_groups: List[List[Dict]] = []
    for ptype in TYPE_ORDER:
        entries = sorted(grouped.get(ptype, []), key=lambda e: e["source"])
        if entries:
            non_empty_groups.append(entries)

    total_entries = sum(len(g) for g in non_empty_groups)
    if total_entries == 0:
        return "[]\n"

    all_lines.append("[")

    for g_idx, group in enumerate(non_empty_groups):
        is_last_group = g_idx == len(non_empty_groups) - 1

        for e_idx, entry in enumerate(group):
            is_last_entry_in_group = e_idx == len(group) - 1
            line = _entry_to_json(entry)
            # Add trailing comma unless it's the very last entry overall
            if is_last_group and is_last_entry_in_group:
                all_lines.append(line)
            else:
                all_lines.append(line + ",")

        # Blank line between groups (not after the last group)
        if not is_last_group:
            all_lines.append("")

    all_lines.append("]")
    return "\n".join(all_lines) + "\n"


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Cosmyx I18N Generator")
    print("=" * 60)

    # Load config
    config = load_config()
    skip_identity: bool = config.get("skip_identity", True)
    languages: Dict = config.get("languages", {})

    if not languages:
        print("ERROR: No languages defined in i18n_config.json")
        return

    print(f"\nConfig loaded: skip_identity={skip_identity}")
    print(f"Languages    : {', '.join(languages.keys())}")

    # Scan profiles
    print("\nScanning profile JSON files...")
    profiles = scan_profile_names(BASE_DIR)
    if not profiles:
        print("WARNING: No profiles found. Check that the Cosmyx profile directory is populated.")
    else:
        by_type = {}
        for p in profiles:
            by_type.setdefault(p["type"], 0)
            by_type[p["type"]] += 1
        print(f"Found {len(profiles)} unique profile names:")
        for ptype, count in sorted(by_type.items()):
            print(f"  {ptype}: {count}")

    # Ensure I18N directory exists
    I18N_DIR.mkdir(exist_ok=True)

    # Generate one file per language
    print("\nGenerating I18N files...")
    identity_warnings: List[Tuple[str, int]] = []

    for lang, lang_config in languages.items():
        grouped = generate_entries_for_language(profiles, lang_config, skip_identity)
        total = sum(len(v) for v in grouped.values())

        output_path = I18N_DIR / f"{lang}.json"
        content = render_i18n_json(grouped)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Count profiles that didn't change (useful diagnostic when skip_identity=False)
        if not skip_identity:
            unchanged = sum(
                1 for grp in grouped.values()
                for e in grp
                if e["source"] == e["translation"]
            )
            if unchanged:
                identity_warnings.append((lang, unchanged))

        print(f"  {lang}.json: {total} entries")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Done! {len(languages)} language files written to: {I18N_DIR}")
    if identity_warnings:
        print("\nNote: the following files contain identity entries (source == translation).")
        print("Set skip_identity=true in i18n_config.json to omit them:")
        for lang, count in identity_warnings:
            print(f"  {lang}.json: {count} identity entries")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
