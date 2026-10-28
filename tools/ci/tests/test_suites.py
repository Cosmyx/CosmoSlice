"""Tests of suite and module-check discovery."""

from pathlib import Path

import pytest
import suites


def make_tree(root: Path, folders: list[str], files: list[str] = ()) -> Path:
    for folder in folders:
        (root / folder).mkdir(parents=True, exist_ok=True)
    for file in files:
        (root / file).parent.mkdir(parents=True, exist_ok=True)
        (root / file).write_text("x\n", encoding="utf-8")
    return root


def test_discovers_suites_under_scripts_and_tools(tmp_path: Path) -> None:
    make_tree(tmp_path, ["scripts/i18n/tests", "scripts/plain", "tools/docker/tests"])
    found = suites.discover_suites(tmp_path)
    assert found == {"i18n": Path("scripts/i18n/tests"), "docker": Path("tools/docker/tests")}


def test_duplicate_suite_name_fails(tmp_path: Path) -> None:
    make_tree(tmp_path, ["scripts/x/tests", "tools/x/tests"])
    with pytest.raises(SystemExit, match="exists twice"):
        suites.discover_suites(tmp_path)


def test_select_all_or_one(tmp_path: Path) -> None:
    found = {"b": Path("scripts/b/tests"), "a": Path("tools/a/tests")}
    assert suites.select_suites(found, None) == [Path("tools/a/tests"), Path("scripts/b/tests")]
    assert suites.select_suites(found, "b") == [Path("scripts/b/tests")]
    with pytest.raises(SystemExit, match="unknown suite 'c'"):
        suites.select_suites(found, "c")


def test_discovers_module_justfiles(tmp_path: Path) -> None:
    make_tree(tmp_path, [], ["scripts/brand_assets/justfile", "tools/x/justfile", "scripts/none/readme.txt"])
    found = suites.discover_module_justfiles(tmp_path)
    assert found == [tmp_path / "scripts/brand_assets/justfile", tmp_path / "tools/x/justfile"]


def test_recipe_names_from_summary() -> None:
    assert suites.recipe_names("check derive stable\n") == {"check", "derive", "stable"}
    assert "check" not in suites.recipe_names("checkout\n")


def test_this_repository_has_its_own_suites() -> None:
    found = suites.discover_suites()
    assert {"ci", "docker", "repo"} <= set(found)
