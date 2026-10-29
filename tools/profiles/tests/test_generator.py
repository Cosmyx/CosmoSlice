"""The Cosmyx vendor index generator on small profile trees."""

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


def preset(name: str, kind: str, inherits: str = "", instantiation: str | None = "true") -> dict:
    data = {"name": name, "type": kind}
    if inherits:
        data["inherits"] = inherits
    if instantiation is not None:
        data["instantiation"] = instantiation
    return data


def make_tree(root: Path) -> Path:
    write(root, "machine/A/Model A.json", {"name": "Model A", "type": "machine_model"})
    write(root, "machine/B/Model B.json", {"name": "Model B", "type": "machine_model"})
    write(root, "machine/fdm_machine_common.json", preset("fdm_machine_common", "machine", instantiation="false"))
    write(root, "machine/A/A 0.4.json", preset("A 0.4", "machine", "fdm_machine_common"))
    write(root, "filament/z base.json", preset("z base", "filament", instantiation="false"))
    write(root, "filament/a child.json", preset("a child", "filament", "z base"))
    write(root, "filament/m other.json", preset("m other", "filament", "z base"))
    write(root, "process/Nova_Can_Out/Mixed Case.json", preset("0.20mm Café", "process"))
    # Everything below is skipped by the scan.
    write(root, "machine/A/._Model A.json", raw=b"\x00\x05\x16\x07 AppleDouble")
    write(root, "process/.smbdelete0001", raw=b"junk")
    write(root, "process/.hidden/x.json", raw=b"not json")
    write(root, "process/readme.txt", raw=b"hello")
    write(root, "I18N/fr.json", {"name": "fr"})
    write(root, "top.json", {"name": "top", "type": "process"})
    return root


def build(root: Path, config: dict | None = None) -> dict:
    return cosmyx_index.build_index(cosmyx_index.scan(root), config or CONFIG, DATE, BRANCH, COMMIT)


def names(index: dict, key: str) -> list[str]:
    return [entry["name"] for entry in index[key]]


def test_classification_by_folder_and_type(tmp_path: Path) -> None:
    index = build(make_tree(tmp_path))
    assert names(index, "machine_model_list") == ["Model A", "Model B"]
    assert names(index, "machine_list") == ["fdm_machine_common", "A 0.4"]
    assert names(index, "filament_list") == ["z base", "a child", "m other"]
    assert names(index, "process_list") == ["0.20mm Café"]


def test_key_order_and_header(tmp_path: Path) -> None:
    index = build(make_tree(tmp_path))
    assert list(index) == [
        "name",
        "url",
        "version",
        "force_update",
        "description",
        "machine_model_list",
        "process_list",
        "filament_list",
        "machine_list",
    ]
    assert index["name"] == "Cosmyx"
    assert index["url"] == CONFIG["url"]
    assert index["version"] == "20261029.130312.00.00"
    assert index["force_update"] == "0"
    assert index["description"] == "Cosmyx profiles of feature/x at 0123456789, committed 2026-10-29T13:03:12Z"


def test_skips_dot_files_non_json_and_other_folders(tmp_path: Path) -> None:
    paths = [r["sub_path"] for r in cosmyx_index.scan(make_tree(tmp_path))]
    assert paths == sorted(paths)
    assert all("/." not in p and not p.startswith(".") for p in paths)
    assert all(p.endswith(".json") for p in paths)
    assert all(p.split("/")[0] in {"machine", "filament", "process"} for p in paths)
    assert len(paths) == 8


def test_sub_paths_keep_the_exact_case_on_disk(tmp_path: Path) -> None:
    index = build(make_tree(tmp_path))
    assert index["process_list"][0]["sub_path"] == "process/Nova_Can_Out/Mixed Case.json"
    assert index["machine_model_list"][0]["sub_path"] == "machine/A/Model A.json"


def test_ties_are_broken_by_name_and_parents_come_first(tmp_path: Path) -> None:
    write(tmp_path, "process/c.json", preset("c", "process", "b"))
    write(tmp_path, "process/b.json", preset("b", "process", "z"))
    write(tmp_path, "process/z.json", preset("z", "process"))
    write(tmp_path, "process/a.json", preset("a", "process"))
    write(tmp_path, "process/y.json", preset("y", "process", "z"))
    index = build(tmp_path)
    assert names(index, "process_list") == ["a", "z", "b", "c", "y"]


def test_machine_model_order_comes_first_then_by_name(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write(tmp_path, "machine/C/Model C.json", {"name": "Model C", "type": "machine_model"})
    index = build(tmp_path, {**CONFIG, "machine_model_order": ["Model B"]})
    assert names(index, "machine_model_list") == ["Model B", "Model A", "Model C"]


def test_exclusions_leave_the_preset_out(tmp_path: Path) -> None:
    make_tree(tmp_path)
    config = {**CONFIG, "exclude": [{"sub_path": "filament/m other.json", "reason": "test"}]}
    assert names(build(tmp_path, config), "filament_list") == ["z base", "a child"]


@pytest.mark.parametrize(
    ("rel", "data", "message"),
    [
        ("process/x.json", {"type": "process", "instantiation": "true"}, "no name"),
        ("process/x.json", {"name": "x", "instantiation": "true"}, "no type"),
        ("process/x.json", {"name": "x", "type": "process"}, "no instantiation"),
        ("process/x.json", preset("x", "filament"), "folder process/"),
        ("machine/x.json", preset("x", "process"), "folder machine/"),
        ("process/x.json", preset("x", "process", "nobody"), "parent 'nobody'"),
        ("process/x.json", preset("x", "process", "fdm_machine_common"), "parent 'fdm_machine_common'"),
        ("filament/dup.json", preset("z base", "filament"), "duplicate name 'z base'"),
    ],
)
def test_invalid_presets_fail(tmp_path: Path, rel: str, data: dict, message: str) -> None:
    make_tree(tmp_path)
    write(tmp_path, rel, data)
    with pytest.raises(cosmyx_index.CosmyxIndexError, match=message):
        build(tmp_path)


def test_unreadable_json_fails(tmp_path: Path) -> None:
    write(tmp_path, "process/broken.json", raw=b"{ not json")
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="broken.json"):
        cosmyx_index.scan(tmp_path)


def test_inheritance_cycle_fails(tmp_path: Path) -> None:
    write(tmp_path, "process/a.json", preset("a", "process", "b"))
    write(tmp_path, "process/b.json", preset("b", "process", "a"))
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="cycle"):
        build(tmp_path)


def test_stale_exclusion_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    config = {**CONFIG, "exclude": [{"sub_path": "process/gone.json", "reason": "test"}]}
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="process/gone.json"):
        build(tmp_path, config)


def test_exclusion_without_reason_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    config = {**CONFIG, "exclude": [{"sub_path": "filament/m other.json", "reason": ""}]}
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="reason"):
        build(tmp_path, config)


def test_stale_machine_model_order_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="Model Z"):
        build(tmp_path, {**CONFIG, "machine_model_order": ["Model Z"]})


def test_bad_branch_or_commit_fails(tmp_path: Path) -> None:
    records = cosmyx_index.scan(make_tree(tmp_path))
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="branch"):
        cosmyx_index.build_index(records, CONFIG, DATE, "", COMMIT)
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="commit"):
        cosmyx_index.build_index(records, CONFIG, DATE, BRANCH, "xyz")


def test_render_is_byte_stable_utf8_lf_with_trailing_newline(tmp_path: Path) -> None:
    make_tree(tmp_path)
    first = cosmyx_index.render(build(tmp_path))
    second = cosmyx_index.render(build(tmp_path))
    assert first == second
    assert b"\r" not in first
    assert first.endswith(b"}\n")
    assert "0.20mm Café".encode() in first
    assert first.startswith(b'{\n    "name": "Cosmyx",\n')


def run_main(args: list[str], runner=None) -> int:
    return cosmyx_index.main(args, runner=runner or fail_runner)


def fail_runner(args: list[str]) -> str:
    raise AssertionError(f"git must not be called: {args}")


def source_args(tmp_path: Path) -> list[str]:
    config = tmp_path / "config.json"
    config.write_text(json.dumps(CONFIG), encoding="utf-8")
    return ["--tree", str(tmp_path / "tree"), "--config", str(config)]


def explicit_args() -> list[str]:
    return ["--commit-date", DATE, "--branch", BRANCH, "--commit", COMMIT]


def test_generate_writes_identical_files(tmp_path: Path) -> None:
    make_tree(tmp_path / "tree")
    out1, out2 = tmp_path / "one.json", tmp_path / "two.json"
    assert run_main(["generate", *source_args(tmp_path), "--out", str(out1), *explicit_args()]) == 0
    assert run_main(["generate", *source_args(tmp_path), "--out", str(out2), *explicit_args()]) == 0
    assert out1.read_bytes() == out2.read_bytes()
    assert json.loads(out1.read_text(encoding="utf-8"))["version"] == "20261029.130312.00.00"


def test_verify_passes_on_a_fresh_index_and_fails_on_a_changed_one(tmp_path: Path, capsys) -> None:
    make_tree(tmp_path / "tree")
    out = tmp_path / "index.json"
    generate = ["generate", *source_args(tmp_path), "--out", str(out), *explicit_args(), "--stamp-presets"]
    assert run_main(generate) == 0
    assert run_main(["verify", *source_args(tmp_path), "--index", str(out), *explicit_args()]) == 0
    out.write_bytes(out.read_bytes().replace(b"\n", b"\r\n"))
    assert run_main(["verify", *source_args(tmp_path), "--index", str(out), *explicit_args()]) == 1
    assert "differs" in capsys.readouterr().err


def test_verify_fails_on_a_missing_index(tmp_path: Path, capsys) -> None:
    make_tree(tmp_path / "tree")
    missing = tmp_path / "nope.json"
    assert run_main(["verify", *source_args(tmp_path), "--index", str(missing), *explicit_args()]) == 1
    assert "nope.json" in capsys.readouterr().err


def test_git_supplies_missing_values(tmp_path: Path) -> None:
    make_tree(tmp_path / "tree")
    calls: list[list[str]] = []
    answers = {
        ("rev-parse", "HEAD"): COMMIT,
        ("log", "-1", "--format=%cI", COMMIT): DATE,
        ("rev-parse", "--abbrev-ref", "HEAD"): BRANCH,
    }

    def runner(args: list[str]) -> str:
        calls.append(args)
        return answers[tuple(args)]

    out = tmp_path / "index.json"
    assert run_main(["generate", *source_args(tmp_path), "--out", str(out)], runner=runner) == 0
    assert len(calls) == 3
    expected = tmp_path / "expected.json"
    assert run_main(["generate", *source_args(tmp_path), "--out", str(expected), *explicit_args()]) == 0
    assert out.read_bytes() == expected.read_bytes()


def test_detached_head_without_branch_fails(tmp_path: Path, capsys) -> None:
    make_tree(tmp_path / "tree")

    def runner(args: list[str]) -> str:
        return {"rev-parse": "HEAD" if "--abbrev-ref" in args else COMMIT, "log": DATE}[args[0]]

    out = tmp_path / "index.json"
    assert run_main(["generate", *source_args(tmp_path), "--out", str(out)], runner=runner) == 1
    assert "--branch" in capsys.readouterr().err
    assert not out.exists()
    assert run_main(["generate", *source_args(tmp_path), "--out", str(out), "--branch", BRANCH], runner=runner) == 0


def test_git_failure_is_reported(tmp_path: Path, capsys) -> None:
    make_tree(tmp_path / "tree")

    def runner(args: list[str]) -> str:
        raise cosmyx_index.CosmyxIndexError("git failed: not a repository")

    assert run_main(["generate", *source_args(tmp_path), "--out", str(tmp_path / "o.json")], runner=runner) == 1
    assert "not a repository" in capsys.readouterr().err


def test_version_subcommand(capsys) -> None:
    assert run_main(["version", "--commit-date", DATE]) == 0
    assert capsys.readouterr().out == "20261029.130312.00.00\n"


def test_records_subcommand_round_trips(tmp_path: Path) -> None:
    make_tree(tmp_path / "tree")
    out = tmp_path / "records.json"
    assert run_main(["records", "--tree", str(tmp_path / "tree"), "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == cosmyx_index.scan(tmp_path / "tree")
    assert out.read_bytes().endswith(b"]\n")
