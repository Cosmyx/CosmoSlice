#!/usr/bin/env python3
"""
Delete all Filament and process folders inside Machine nozzle subfolders.

Targets: Machine/**/<nozzle>/Filament  (case-insensitive)
         Machine/**/<nozzle>/process   (case-insensitive)

Usage:
    python ztool_delete_machine_filament_process.py           # dry-run (safe)
    python ztool_delete_machine_filament_process.py --delete  # actually delete
"""

import os
import sys
import shutil
from pathlib import Path

MACHINE_DIR = Path(__file__).parent / "Machine"
TARGET_NAMES = {"filament", "process"}


def find_targets(root: Path):
    targets = []
    for dirpath, dirnames, _ in os.walk(root):
        # Collect matches before pruning so we don't descend into them
        matches = [d for d in dirnames if d.lower() in TARGET_NAMES]
        for d in matches:
            targets.append(Path(dirpath) / d)
        # Prune matched dirs so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d.lower() not in TARGET_NAMES]
    return targets


def main():
    dry_run = "--delete" not in sys.argv

    if not MACHINE_DIR.is_dir():
        print(f"ERROR: Machine directory not found:\n  {MACHINE_DIR}")
        sys.exit(1)

    targets = find_targets(MACHINE_DIR)

    if not targets:
        print("No Filament or process folders found.")
        return

    mode = "DRY RUN" if dry_run else "DELETE"
    print(f"[{mode}] Found {len(targets)} folder(s):\n")
    for t in sorted(targets):
        print(f"  {t.relative_to(MACHINE_DIR)}")

    if dry_run:
        print(f"\nRun with --delete to actually remove these {len(targets)} folder(s).")
        return

    print(f"\nDeleting {len(targets)} folder(s)...")
    errors = 0
    for t in sorted(targets):
        try:
            shutil.rmtree(t)
            print(f"  deleted: {t.relative_to(MACHINE_DIR)}")
        except Exception as e:
            print(f"  ERROR: {t.relative_to(MACHINE_DIR)}: {e}")
            errors += 1

    if errors:
        print(f"\nDone with {errors} error(s).")
    else:
        print(f"\nDone. {len(targets)} folder(s) removed.")


if __name__ == "__main__":
    main()
