#!/usr/bin/env python3
"""
Runner: executes all Cosmyx generation ztools in the correct order.

Order:
  1. ztool_generate_filament_variants.py
  2. ztool_generate_process_variants.py
  3. ztool_generate_filament_HT.py
  4. ztool_generate_filament_ceram.py
  5. ztool_normalize_common_libraries.py
  6. ztool_update_versions.py
  7. ztool_generate_cosmyx_json.py

Usage:
    python ztool_run_all.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

STEPS = [
    "ztool_generate_filament_variants.py",
    "ztool_generate_process_variants.py",
    "ztool_generate_filament_HT.py",
    "ztool_generate_filament_ceram.py",
    "ztool_normalize_common_libraries.py",
    "ztool_update_versions.py",
    "ztool_generate_cosmyx_json.py",
]


def run_step(script: str) -> bool:
    path = HERE / script
    if not path.exists():
        print(f"  ERROR: script not found: {path}")
        return False

    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(HERE),
    )
    return result.returncode == 0


def main():
    total = len(STEPS)
    for i, script in enumerate(STEPS, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{total}] Running: {script}")
        print("=" * 60)

        ok = run_step(script)
        if not ok:
            print(f"\nABORTED: {script} failed (exit code non-zero). Fix the error and re-run.")
            sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"All {total} steps completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
