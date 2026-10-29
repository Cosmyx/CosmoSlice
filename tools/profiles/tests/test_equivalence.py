"""The generated index matches the hand-maintained one it replaces, and covers the live profile tree.

Both fixtures are frozen at 3cc7dc1df7 so the test never needs git history: `cosmyx_index_3cc7dc1df7.json` is a
verbatim copy of resources/profiles/cosmyx.json, and `records_3cc7dc1df7.json` is `cosmyx_index.py records` run on
resources/profiles/cosmyx at that commit.
"""

from __future__ import annotations

import json
from pathlib import Path

import cosmyx_index

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LISTS = ("machine_model_list", "process_list", "filament_list", "machine_list")
DATE = "2026-10-29T13:03:12Z"
BRANCH = "ci/generate-cosmyx-index"
COMMIT = "3cc7dc1df7" + "0" * 30


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def generated_from_fixture() -> dict:
    config = cosmyx_index.load_config(cosmyx_index.DEFAULT_CONFIG)
    return cosmyx_index.build_index(load("records_3cc7dc1df7.json"), config, DATE, BRANCH, COMMIT)


def test_machine_models_keep_the_wizard_order() -> None:
    assert generated_from_fixture()["machine_model_list"] == load("cosmyx_index_3cc7dc1df7.json")["machine_model_list"]


def test_every_list_has_the_same_entries() -> None:
    generated, legacy = generated_from_fixture(), load("cosmyx_index_3cc7dc1df7.json")
    for key in LISTS:
        as_set = {(e["name"], e["sub_path"]) for e in generated[key]}
        assert as_set == {(e["name"], e["sub_path"]) for e in legacy[key]}, key
        assert len(as_set) == len(generated[key]), key


def test_only_version_and_description_differ() -> None:
    generated, legacy = generated_from_fixture(), load("cosmyx_index_3cc7dc1df7.json")
    assert list(generated) == list(legacy)
    differing = {key for key in legacy if key not in LISTS and generated[key] != legacy[key]}
    assert differing == {"version", "description"}


def test_parents_come_first_in_every_list() -> None:
    generated = generated_from_fixture()
    parents = {r["name"]: r["inherits"] for r in load("records_3cc7dc1df7.json")}
    for key in LISTS[1:]:
        seen: set[str] = set()
        for entry in generated[key]:
            parent = parents[entry["name"]]
            assert not parent or parent in seen, (key, entry["name"])
            seen.add(entry["name"])


def test_real_tree_generates_and_covers_every_preset() -> None:
    config = cosmyx_index.load_config(cosmyx_index.DEFAULT_CONFIG)
    index = cosmyx_index.build_index(cosmyx_index.scan(cosmyx_index.DEFAULT_TREE), config, DATE, BRANCH, COMMIT)
    listed = {e["sub_path"] for key in LISTS for e in index[key]}
    excluded = {e["sub_path"] for e in config["exclude"]}
    on_disk = {
        p.relative_to(cosmyx_index.DEFAULT_TREE).as_posix()
        for folder in ("machine", "filament", "process")
        for p in (cosmyx_index.DEFAULT_TREE / folder).rglob("*.json")
        if not any(part.startswith(".") for part in p.relative_to(cosmyx_index.DEFAULT_TREE).parts)
    }
    assert listed | excluded == on_disk
    assert not listed & excluded
