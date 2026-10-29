"""Every packaged Cosmyx preset carries the version of the generated index; the tracked presets carry none."""

from __future__ import annotations

import json
from pathlib import Path

import cosmyx_index
import pytest

DATE = "2026-10-29T14:03:12+01:00"
BRANCH = "feature/x"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
CONFIG = {
    "name": "Cosmyx",
    "url": "http://example.invalid/Cosmyx.json",
    "force_update": "0",
    "machine_model_order": [],
    "exclude": [],
}


def write(root: Path, rel: str, data: dict | None = None, raw: bytes | None = None) -> None:
    path = root.joinpath(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if raw is not None else json.dumps(data, indent=4).encode("utf-8"))


def preset(name: str, kind: str, inherits: str = "") -> dict:
    data = {"type": kind, "name": name, "instantiation": "true"}
    if inherits:
        data["inherits"] = inherits
    return data


def make_tree(root: Path) -> Path:
    write(root, "machine/A/Model A.json", {"type": "machine_model", "name": "Model A"})
    write(root, "machine/A/A 0.4.json", preset("A 0.4", "machine"))
    write(root, "filament/f.json", preset("f", "filament"))
    write(root, "process/p.json", preset("p", "process"))
    # Skipped by the scan, so never stamped.
    write(root, "process/readme.txt", raw=b"hello")
    write(root, "I18N/fr.json", {"name": "fr"})
    return root


VERSION = cosmyx_index.version_from_commit_date(DATE)


def stamped(tree: Path) -> dict[str, str | None]:
    return {
        r["sub_path"]: json.loads((tree / r["sub_path"]).read_text("utf-8")).get("version")
        for r in cosmyx_index.scan(tree)
    }


def test_stamp_inserts_and_replaces_the_version(tmp_path: Path) -> None:
    tree = make_tree(tmp_path)
    write(
        tree, "process/old.json", {"name": "old", "type": "process", "version": "01.07.00.18", "instantiation": "true"}
    )
    count = cosmyx_index.stamp_presets(tree, VERSION)
    versions = stamped(tree)
    assert count == len(versions)
    assert set(versions.values()) == {VERSION}


def test_stamp_changes_only_the_version_line(tmp_path: Path) -> None:
    raw = '{\n    "type": "process",\n    "name": "p",\n    "version": "1.7.0.18",\n    "instantiation": "true"\n}\n'
    write(tmp_path, "process/p.json", raw=raw.encode())
    cosmyx_index.stamp_presets(tmp_path, VERSION)
    assert (tmp_path / "process" / "p.json").read_text("utf-8") == raw.replace("1.7.0.18", VERSION)


def test_stamp_adds_the_version_as_the_first_key(tmp_path: Path) -> None:
    raw = '{\n    "type": "process",\n    "name": "p"\n}\n'
    write(tmp_path, "process/p.json", raw=raw.encode())
    cosmyx_index.stamp_presets(tmp_path, VERSION)
    text = (tmp_path / "process" / "p.json").read_text("utf-8")
    assert text == '{\n    "version": "' + VERSION + '",\n    "type": "process",\n    "name": "p"\n}\n'


def test_stamp_is_idempotent_and_skips_what_the_scan_skips(tmp_path: Path) -> None:
    tree = make_tree(tmp_path)
    cosmyx_index.stamp_presets(tree, VERSION)
    before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}
    cosmyx_index.stamp_presets(tree, VERSION)
    assert {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()} == before
    assert json.loads((tree / "I18N" / "fr.json").read_text("utf-8")) == {"name": "fr"}
    assert (tree / "process" / "readme.txt").read_bytes() == b"hello"


def test_stamp_rejects_a_nested_version_key(tmp_path: Path) -> None:
    data = preset("p", "process")
    data["extra"] = {"version": "x"}
    write(tmp_path, "process/p.json", raw=json.dumps(data, indent=4).encode())
    with pytest.raises(cosmyx_index.CosmyxIndexError):
        cosmyx_index.stamp_presets(tmp_path, VERSION)


def test_check_reports_presets_with_another_or_no_version(tmp_path: Path) -> None:
    tree = make_tree(tmp_path)
    cosmyx_index.stamp_presets(tree, VERSION)
    write(tree, "process/late.json", preset("late", "process"))
    write(tree, "process/old.json", {**preset("old", "process"), "version": "01.07.00.18"})
    assert cosmyx_index.check_preset_versions(tree, VERSION) == ["process/late.json", "process/old.json"]


def test_generate_stamps_only_when_asked(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "cosmyx")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(CONFIG), encoding="utf-8")
    out = tmp_path / "cosmyx.json"
    source = [
        "--tree",
        str(tree),
        "--config",
        str(config),
        "--commit-date",
        DATE,
        "--branch",
        BRANCH,
        "--commit",
        COMMIT,
    ]
    assert cosmyx_index.main(["generate", *source, "--out", str(out)]) == 0
    assert set(stamped(tree).values()) == {None}
    assert cosmyx_index.main(["generate", *source, "--out", str(out), "--stamp-presets"]) == 0
    assert set(stamped(tree).values()) == {json.loads(out.read_text("utf-8"))["version"]}


def test_verify_checks_the_packaged_presets(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "src" / "cosmyx")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(CONFIG), encoding="utf-8")
    source = [
        "--tree",
        str(tree),
        "--config",
        str(config),
        "--commit-date",
        DATE,
        "--branch",
        BRANCH,
        "--commit",
        COMMIT,
    ]
    package = tmp_path / "package" / "profiles"
    package.mkdir(parents=True)
    index = package / "cosmyx.json"
    assert cosmyx_index.main(["generate", *source, "--out", str(index), "--stamp-presets"]) == 0
    make_tree(package / "cosmyx")
    assert cosmyx_index.main(["verify", *source, "--index", str(index)]) == 1
    cosmyx_index.stamp_presets(package / "cosmyx", VERSION)
    assert cosmyx_index.main(["verify", *source, "--index", str(index)]) == 0


def test_verify_fails_without_packaged_presets(tmp_path: Path, capsys) -> None:
    tree = make_tree(tmp_path / "src" / "cosmyx")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(CONFIG), encoding="utf-8")
    source = [
        "--tree",
        str(tree),
        "--config",
        str(config),
        "--commit-date",
        DATE,
        "--branch",
        BRANCH,
        "--commit",
        COMMIT,
    ]
    index = tmp_path / "package" / "cosmyx.json"
    index.parent.mkdir()
    assert cosmyx_index.main(["generate", *source, "--out", str(index)]) == 0
    assert cosmyx_index.main(["verify", *source, "--index", str(index)]) == 1
    assert "no packaged presets" in capsys.readouterr().err


def test_tracked_presets_carry_no_version() -> None:
    """The version comes from the build only (D-015): a tracked value would always be stale."""
    assert {k: v for k, v in stamped(cosmyx_index.DEFAULT_TREE).items() if v is not None} == {}
