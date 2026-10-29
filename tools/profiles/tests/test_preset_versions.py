"""Every packaged Cosmyx preset carries the version of the generated index; the tracked presets carry none."""

from __future__ import annotations

import json
import shutil
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


@pytest.mark.parametrize("newline, indent", [("\n", "\t"), ("\r\n", "  ")])
def test_stamp_keeps_the_indentation_and_line_endings(tmp_path: Path, newline: str, indent: str) -> None:
    raw = "{" + newline + indent + '"type": "process",' + newline + indent + '"name": "p"' + newline + "}" + newline
    write(tmp_path, "process/p.json", raw=raw.encode())
    cosmyx_index.stamp_presets(tmp_path, VERSION)
    expected = "{" + newline + indent + f'"version": "{VERSION}",' + raw[1:]
    assert (tmp_path / "process" / "p.json").read_bytes() == expected.encode()


@pytest.mark.parametrize(
    "raw, message",
    [
        ('{"type": "process", "name": "p"}', "multi-line"),
        ('{\n    "type": "process",\n    "name": "p",\n    "version": 1\n}\n', "single top-level string"),
        ('{\n    "type": "process",\n    "name": "p",\n    "version": "a\\"b"\n}\n', "single top-level string"),
    ],
)
def test_stamp_refuses_what_it_cannot_edit_safely(tmp_path: Path, raw: str, message: str) -> None:
    write(tmp_path, "process/p.json", raw=raw.encode())
    with pytest.raises(cosmyx_index.CosmyxIndexError, match=message):
        cosmyx_index.stamp_presets(tmp_path, VERSION)


def test_stamp_writes_nothing_when_one_preset_is_refused(tmp_path: Path) -> None:
    tree = make_tree(tmp_path)
    write(tree, "process/zz bad.json", raw=b'{"type": "process", "name": "bad"}')
    before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}
    with pytest.raises(cosmyx_index.CosmyxIndexError):
        cosmyx_index.stamp_presets(tree, VERSION)
    assert {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()} == before


def test_the_real_tree_stamps_cleanly(tmp_path: Path) -> None:
    """Catches a preset the stamper refuses before CI's build does (a pack import, a hand edit)."""
    copy = tmp_path / "cosmyx"
    shutil.copytree(cosmyx_index.DEFAULT_TREE, copy)
    cosmyx_index.stamp_presets(copy, VERSION)
    assert cosmyx_index.check_preset_versions(copy, VERSION) == []
    for record in cosmyx_index.scan(cosmyx_index.DEFAULT_TREE):
        original = json.loads(
            (cosmyx_index.DEFAULT_TREE / record["sub_path"]).read_text("utf-8"), object_pairs_hook=list
        )
        stamped_pairs = json.loads((copy / record["sub_path"]).read_text("utf-8"), object_pairs_hook=list)
        assert stamped_pairs == [("version", VERSION), *original], record["sub_path"]


def test_tracked_presets_carry_no_version() -> None:
    """The version comes from the build only (D-015): a tracked value would always be stale."""
    assert {k: v for k, v in stamped(cosmyx_index.DEFAULT_TREE).items() if v is not None} == {}
