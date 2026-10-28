"""Tests of the Docker launcher: tags, commands and mounts, without calling Docker."""

from pathlib import Path

import pytest
import run


def make_context(tmp_path: Path, files: dict[str, bytes]) -> Path:
    folder = tmp_path / "ci"
    for name, data in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return folder


def test_tag_depends_on_every_context_file(tmp_path: Path) -> None:
    folder = make_context(tmp_path, {"Dockerfile": b"FROM x\n", "requirements.txt": b"a==1\n"})
    first = run.image_tag("ci", folder)
    assert first.startswith("cosmoslice-ci:")
    assert run.image_tag("ci", folder) == first
    (folder / "requirements.txt").write_bytes(b"a==2\n")
    assert run.image_tag("ci", folder) != first


def test_tag_ignores_pycache(tmp_path: Path) -> None:
    folder = make_context(tmp_path, {"Dockerfile": b"FROM x\n"})
    before = run.image_tag("ci", folder)
    make_context(tmp_path, {"__pycache__/x.pyc": b"junk"})
    assert run.image_tag("ci", folder) == before


def test_missing_image_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no Dockerfile"):
        run.context_dir("nope", tmp_path)


def test_build_is_always_amd64(tmp_path: Path) -> None:
    cmd = run.build_command("cosmoslice-ci:abc", tmp_path)
    assert cmd[:2] == ["docker", "build"]
    assert cmd[cmd.index("--platform") + 1] == "linux/amd64"
    assert cmd[-1] == str(tmp_path)


def test_run_mounts_repo_and_passes_command(tmp_path: Path) -> None:
    cmd = run.run_command("tag:1", ["pytest", "-q"], repo_root=tmp_path, user=[])
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert cmd[cmd.index("--platform") + 1] == "linux/amd64"
    assert cmd[cmd.index("--mount") + 1] == f"type=bind,source={tmp_path},target=/repo"
    assert cmd[cmd.index("--workdir") + 1] == "/repo"
    assert "--user" not in cmd
    assert cmd[-3:] == ["tag:1", "pytest", "-q"]


def test_run_passes_user_when_given(tmp_path: Path) -> None:
    cmd = run.run_command("tag:1", ["true"], repo_root=tmp_path, user=["--user", "501:20"])
    assert cmd[cmd.index("--user") + 1] == "501:20"


def test_user_args_follow_the_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(run.os, "getgid", lambda: 100, raising=False)
    assert run.user_args() == ["--user", "1000:100"]
    monkeypatch.delattr(run.os, "getuid", raising=False)
    assert run.user_args() == []


def test_workdir_is_posix_below_mount() -> None:
    assert run.container_workdir(None) == "/repo"
    assert run.container_workdir(str(Path("scripts") / "brand_assets")) == "/repo/scripts/brand_assets"


def test_parse_args_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        run.parse_args([])
    assert run.parse_args(["--", "ruff", "check"]).command == ["ruff", "check"]
    assert run.parse_args(["--build-only"]).build_only
