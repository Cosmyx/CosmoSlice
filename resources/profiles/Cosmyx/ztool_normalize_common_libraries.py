#!/usr/bin/env python3
"""
Script to normalize the Common Filament Library and Common Process Library.

Actions:
  1. Replaces all 'compatible_printers' values with ["Cosmyx Machines"]
     in BOTH the Common Filament Library and the Common Process Library.
  2. In the Common Filament Library ONLY:
     - Renames '@Cosmyx Nova' to '@Cosmyx Common' in every filename.
     - Replaces '@Cosmyx Nova' with '@Cosmyx Common' in all JSON string
       field values (name, inherits, compatible_printers, etc.).
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ==================== CONFIGURATION ====================

BASE_DIR = Path(__file__).parent
FILAMENT_LIBRARY_DIR = BASE_DIR / 'Common Filament library'
PROCESS_LIBRARY_DIR  = BASE_DIR / 'Common Process Library'

COSMYX_MACHINES = ["Cosmyx Machines"]


# ==================== DATA STRUCTURES ====================

@dataclass
class NormalizeResult:
    files_compatible_updated: List[Path] = field(default_factory=list)
    files_nova_renamed:       List[Tuple[Path, Path]] = field(default_factory=list)
    files_nova_content_fixed: List[Path] = field(default_factory=list)
    errors:                   List[Tuple[Path, str]] = field(default_factory=list)


# ==================== HELPERS ====================

def replace_compatible_printers(data: dict) -> bool:
    """
    Set compatible_printers to ["Cosmyx Machines"].
    Returns True if the value was changed.
    """
    if 'compatible_printers' in data:
        if data['compatible_printers'] != COSMYX_MACHINES:
            data['compatible_printers'] = COSMYX_MACHINES
            return True
    return False


def replace_nova_in_values(data: dict) -> bool:
    """
    Recursively replace '@Cosmyx Nova' with '@Cosmyx Common' in all
    string values (and strings inside lists) of a dict.
    Returns True if anything was changed.
    """
    changed = False
    for key, value in data.items():
        if isinstance(value, str) and '@Cosmyx Nova' in value:
            data[key] = value.replace('@Cosmyx Nova', '@Cosmyx Common')
            changed = True
        elif isinstance(value, list):
            new_list = []
            for item in value:
                if isinstance(item, str) and '@Cosmyx Nova' in item:
                    new_list.append(item.replace('@Cosmyx Nova', '@Cosmyx Common'))
                    changed = True
                else:
                    new_list.append(item)
            data[key] = new_list
        elif isinstance(value, dict):
            if replace_nova_in_values(value):
                changed = True
    return changed


def process_json_file(file_path: Path, fix_nova_content: bool) -> Tuple[bool, bool]:
    """
    Load, modify, and save a JSON file.

    Returns:
        (compatible_changed, nova_content_changed)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    compatible_changed = replace_compatible_printers(data)
    nova_content_changed = fix_nova_content and replace_nova_in_values(data)

    if compatible_changed or nova_content_changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    return compatible_changed, nova_content_changed


def rename_if_needed(file_path: Path) -> Optional[Path]:
    """
    If the filename contains '@Cosmyx Nova', rename it to '@Cosmyx Common'.
    Returns the new Path if renamed, None otherwise.
    """
    if '@Cosmyx Nova' in file_path.name:
        new_name = file_path.name.replace('@Cosmyx Nova', '@Cosmyx Common')
        new_path = file_path.parent / new_name
        file_path.rename(new_path)
        return new_path
    return None


def process_library(library_dir: Path, fix_nova: bool, result: NormalizeResult):
    """
    Walk all JSON files in library_dir and apply normalisation.

    fix_nova=True  → also rename files and fix content  (filament library)
    fix_nova=False → only replace compatible_printers    (process library)
    """
    if not library_dir.exists():
        print(f"  Warning: directory not found: {library_dir}")
        return

    for file_path in sorted(library_dir.rglob('*.json')):
        try:
            compatible_changed, nova_changed = process_json_file(file_path, fix_nova)

            if compatible_changed:
                result.files_compatible_updated.append(file_path)
            if nova_changed:
                result.files_nova_content_fixed.append(file_path)

            if fix_nova:
                new_path = rename_if_needed(file_path)
                if new_path:
                    result.files_nova_renamed.append((file_path, new_path))

        except json.JSONDecodeError as e:
            msg = f"JSON parse error: {e}"
            result.errors.append((file_path, msg))
            print(f"  Warning: {file_path.name} — {msg}")
        except Exception as e:
            result.errors.append((file_path, str(e)))
            print(f"  Error: {file_path.name} — {e}")


# ==================== MAIN ====================

def main():
    result = NormalizeResult()

    print("=" * 60)
    print("Common Library Normalizer")
    print("=" * 60)

    print(f"\n[1/2] Common Filament Library  (compatible_printers + rename @Cosmyx Nova)")
    process_library(FILAMENT_LIBRARY_DIR, fix_nova=True, result=result)

    print(f"[2/2] Common Process Library   (compatible_printers only)")
    process_library(PROCESS_LIBRARY_DIR, fix_nova=False, result=result)

    # ---- Report ----
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  compatible_printers updated : {len(result.files_compatible_updated)}")
    print(f"  files renamed (Nova→Common) : {len(result.files_nova_renamed)}")
    print(f"  content fixed (Nova→Common) : {len(result.files_nova_content_fixed)}")
    print(f"  errors                      : {len(result.errors)}")

    if result.files_nova_renamed:
        print("\nRenamed files:")
        for old, new in result.files_nova_renamed:
            print(f"  {old.name}")
            print(f"    → {new.name}")

    if result.errors:
        print("\nErrors:")
        for path, err in result.errors:
            print(f"  {path.name}: {err}")


if __name__ == "__main__":
    main()
