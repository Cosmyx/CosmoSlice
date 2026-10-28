"""Every `sub_path` declared by a vendor index must exist with its exact case.

macOS and Windows resolve paths case-insensitively, so a wrong case loads fine there and fails on Linux.
"""

import json
import os
from pathlib import Path

import pytest

PROFILES = Path(__file__).resolve().parents[3] / "resources" / "profiles"


def vendor_sub_paths() -> list[tuple[str, str]]:
    found = []
    for index in sorted(PROFILES.glob("*.json")):
        data = json.loads(index.read_text(encoding="utf-8"))
        for value in data.values():
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, dict) and "sub_path" in item:
                    found.append((index.stem, item["sub_path"]))
    return found


def exists_with_exact_case(base: Path, rel: str) -> bool:
    current = base
    for part in rel.split("/"):
        if not current.is_dir() or part not in os.listdir(current):
            return False
        current = current / part
    return True


def test_vendor_indexes_declare_sub_paths():
    assert vendor_sub_paths()


@pytest.mark.parametrize(("vendor", "sub_path"), vendor_sub_paths())
def test_sub_path_exists_with_exact_case(vendor: str, sub_path: str):
    assert exists_with_exact_case(PROFILES / vendor, sub_path), f"{vendor}: {sub_path}"


def test_exact_case_check_rejects_a_wrong_case(tmp_path: Path):
    (tmp_path / "Machine").mkdir()
    (tmp_path / "Machine" / "a.json").write_text("{}", encoding="utf-8")
    assert exists_with_exact_case(tmp_path, "Machine/a.json")
    assert not exists_with_exact_case(tmp_path, "machine/a.json")
