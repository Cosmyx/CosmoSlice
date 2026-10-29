"""Every `sub_path` declared by a vendor index must exist with its exact case.

macOS and Windows resolve paths case-insensitively, so a wrong case loads fine there and fails on Linux.
The Cosmyx index is not tracked (D-013): its entries are generated in memory from the tree, and a cosmyx.json left
on disk by `just profiles-index` is ignored.
"""

import json
import os
from pathlib import Path

import cosmyx_index
import pytest

PROFILES = Path(__file__).resolve().parents[3] / "resources" / "profiles"
GENERATED = cosmyx_index.DEFAULT_OUT.name


def vendor_sub_paths(profiles: Path = PROFILES) -> list[tuple[str, str]]:
    """Sub-paths of the committed vendor indexes on disk (the generated Cosmyx index excluded)."""
    found = []
    for index in sorted(profiles.glob("*.json")):
        if index.name == GENERATED:
            continue
        data = json.loads(index.read_text(encoding="utf-8"))
        for value in data.values():
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, dict) and "sub_path" in item:
                    found.append((index.stem, item["sub_path"]))
    return found


def cosmyx_sub_paths() -> list[tuple[str, str]]:
    """Sub-paths of the Cosmyx index generated in memory from the live tree (fixed git inputs: only paths matter)."""
    config = cosmyx_index.load_config(cosmyx_index.DEFAULT_CONFIG)
    records = cosmyx_index.scan(cosmyx_index.DEFAULT_TREE)
    index = cosmyx_index.build_index(records, config, "2026-01-01T00:00:00Z", "test", "0" * 40)
    vendor = cosmyx_index.DEFAULT_TREE.name
    return [(vendor, e["sub_path"]) for v in index.values() if isinstance(v, list) for e in v]


def exists_with_exact_case(base: Path, rel: str) -> bool:
    current = base
    for part in rel.split("/"):
        if not current.is_dir() or part not in os.listdir(current):
            return False
        current = current / part
    return True


def test_vendor_indexes_declare_sub_paths():
    assert vendor_sub_paths()


@pytest.mark.parametrize(("vendor", "sub_path"), vendor_sub_paths() + cosmyx_sub_paths())
def test_sub_path_exists_with_exact_case(vendor: str, sub_path: str):
    assert exists_with_exact_case(PROFILES / vendor, sub_path), f"{vendor}: {sub_path}"


def test_the_generated_cosmyx_index_replaces_the_file_on_disk(tmp_path: Path):
    (tmp_path / "cosmyx.json").write_text('{"process_list": [{"sub_path": "stale.json"}]}', encoding="utf-8")
    (tmp_path / "other.json").write_text('{"process_list": [{"sub_path": "p/a.json"}]}', encoding="utf-8")
    assert vendor_sub_paths(tmp_path) == [("other", "p/a.json")]


def test_cosmyx_sub_paths_are_generated_from_the_tree():
    found = cosmyx_sub_paths()
    assert ("cosmyx", "machine/Nova/Cosmyx Nova.json") in found
    assert len(found) == len(set(found)) > 100


def test_exact_case_check_rejects_a_wrong_case(tmp_path: Path):
    (tmp_path / "Machine").mkdir()
    (tmp_path / "Machine" / "a.json").write_text("{}", encoding="utf-8")
    assert exists_with_exact_case(tmp_path, "Machine/a.json")
    assert not exists_with_exact_case(tmp_path, "machine/a.json")
