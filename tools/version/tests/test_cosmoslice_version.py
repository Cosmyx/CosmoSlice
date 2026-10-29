"""The CosmoSlice version is built from version.inc, the same way for CMake and for the CI build names."""

from __future__ import annotations

from pathlib import Path

import cosmoslice_version
import pytest

INC = """\
# comment with set(FAKE "x")
set(SoftFever_VERSION "2.3.1")
set(COSMYX_PATCH_VERSION "5")
set(COSMOSLICE_VERSION "${SoftFever_VERSION}-${COSMYX_PATCH_VERSION}")
if(NOT DEFINED X)
set(X "1")
endif()
"""


def write(tmp_path: Path, text: str = INC) -> Path:
    path = tmp_path / "version.inc"
    path.write_bytes(text.encode())
    return path


def test_expands_the_cmake_definition(tmp_path: Path) -> None:
    assert cosmoslice_version.version(write(tmp_path)) == "2.3.1-5"


def test_follows_a_change_of_either_part(tmp_path: Path) -> None:
    text = INC.replace('"2.3.1"', '"2.4.0"').replace('"5"', '"12"')
    assert cosmoslice_version.version(write(tmp_path, text)) == "2.4.0-12"


def test_comments_are_ignored(tmp_path: Path) -> None:
    assert "FAKE" not in cosmoslice_version.read_sets(write(tmp_path))


@pytest.mark.parametrize(
    "text",
    [
        'set(SoftFever_VERSION "2.3.1")\n',
        INC.replace("${COSMYX_PATCH_VERSION}", "${UNKNOWN}"),
        INC.replace('"5"', '""'),
    ],
)
def test_rejects_a_missing_or_empty_part(tmp_path: Path, text: str) -> None:
    with pytest.raises(cosmoslice_version.VersionError):
        cosmoslice_version.version(write(tmp_path, text))


def test_build_tag_appends_the_commit() -> None:
    assert cosmoslice_version.build_tag("2.3.1-5", "aa9dac8") == "2.3.1-5_aa9dac8"


@pytest.mark.parametrize("commit", ["", "aa9 dac8", "AA9DAC8", "zz9dac8"])
def test_build_tag_rejects_a_bad_commit(commit: str) -> None:
    with pytest.raises(cosmoslice_version.VersionError):
        cosmoslice_version.build_tag("2.3.1-5", commit)


def test_default_commit_is_the_short_hash_cmake_embeds(tmp_path: Path) -> None:
    calls = []

    def run(args: list[str]) -> str:
        calls.append(args)
        return "aa9dac8\n"

    assert cosmoslice_version.head_commit(run) == "aa9dac8"
    assert calls == [["git", "log", "-1", "--format=%h"]]


def test_cli_prints_the_version_and_the_build_tag(tmp_path: Path, capsys) -> None:
    inc = write(tmp_path)
    assert cosmoslice_version.main(["version", "--inc", str(inc)]) == 0
    assert capsys.readouterr().out == "2.3.1-5\n"
    assert cosmoslice_version.main(["build-tag", "--inc", str(inc), "--commit", "aa9dac8"]) == 0
    assert capsys.readouterr().out == "2.3.1-5_aa9dac8\n"


def test_cli_reports_an_error(tmp_path: Path, capsys) -> None:
    assert cosmoslice_version.main(["version", "--inc", str(write(tmp_path, ""))]) == 1
    assert "COSMOSLICE_VERSION" in capsys.readouterr().err


def test_real_version_inc() -> None:
    assert cosmoslice_version.version(cosmoslice_version.DEFAULT_INC) == "2.3.1-5"
