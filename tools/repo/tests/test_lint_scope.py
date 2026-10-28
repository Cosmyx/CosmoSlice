"""The lint covers the CosmoSlice modules below scripts/ and tools/, and skips only the legacy upstream scripts."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def linted_files() -> set[str]:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-files", "scripts", "tools"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = set()
    for line in result.stdout.splitlines():
        path = Path(line.strip())
        if path.is_absolute():
            files.add(path.resolve().relative_to(REPO_ROOT.resolve()).as_posix())
    return files


def test_module_files_are_linted() -> None:
    files = linted_files()
    assert "scripts/i18n/rename_msgids.py" in files
    assert "tools/docker/run.py" in files


def test_legacy_scripts_are_excluded() -> None:
    files = linted_files()
    assert "scripts/update_pot.py" not in files
    assert not any(f.startswith(("scripts/flatpak/", "scripts/linux.d/")) for f in files)
