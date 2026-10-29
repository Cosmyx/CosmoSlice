"""Build the CosmoSlice version from version.inc, as CMake does, for the CI build names.

version.inc defines COSMOSLICE_VERSION from SoftFever_VERSION (the OrcaSlicer base) and COSMYX_PATCH_VERSION; this
expands that same definition instead of repeating its format, so the app and the build names cannot disagree.

    cosmoslice_version.py version    [--inc PATH]                 -> 2.3.1-5
    cosmoslice_version.py build-tag  [--inc PATH] [--commit SHA]  -> 2.3.1-5_aa9dac8

The commit defaults to `git log -1 --format=%h`, the abbreviated hash (7 characters or more) CMakeLists.txt embeds
as GIT_COMMIT_HASH. Only quoted `set(NAME "value")` lines are read; anything else in version.inc is ignored.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INC = REPO_ROOT / "version.inc"
VERSION_VAR = "COSMOSLICE_VERSION"
SET = re.compile(r'^\s*set\(\s*(\w+)\s+"([^"]*)"\s*\)', re.MULTILINE)
REF = re.compile(r"\$\{(\w+)\}")
COMMIT = re.compile(r"[0-9a-f]{7,40}")


class VersionError(Exception):
    pass


def read_sets(inc: Path) -> dict[str, str]:
    """Every `set(NAME "value")` of the file in order, with ${VAR} expanded from the earlier ones."""
    text = "\n".join(line.split("#", 1)[0] for line in inc.read_text(encoding="utf-8").splitlines())
    values: dict[str, str] = {}
    for name, raw in SET.findall(text):
        missing = [ref for ref in REF.findall(raw) if ref not in values]
        if missing:
            raise VersionError(f"{inc.name}: {name} uses ${{{missing[0]}}}, which is not set before it")
        values[name] = REF.sub(lambda match: values[match[1]], raw)
    return values


def version(inc: Path = DEFAULT_INC) -> str:
    value = read_sets(inc).get(VERSION_VAR, "")
    if not re.fullmatch(r"\d+\.\d+\.\d+-[0-9A-Za-z.]+", value):
        raise VersionError(f"{inc.name}: {VERSION_VAR} is {value!r}, expected <major>.<minor>.<patch>-<cosmyx patch>")
    return value


def build_tag(app_version: str, commit: str) -> str:
    if not COMMIT.fullmatch(commit):
        raise VersionError(f"commit {commit!r} is not a lower-case hex hash")
    return f"{app_version}_{commit}"


def git_runner(cwd: Path) -> Callable[[list[str]], str]:
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout

    return run


def head_commit(run: Callable[[list[str]], str]) -> str:
    return run(["git", "log", "-1", "--format=%h"]).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("version", "build-tag"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--inc", type=Path, default=DEFAULT_INC)
        if name == "build-tag":
            cmd.add_argument("--commit", help="short commit hash (default: HEAD, as CMake embeds it)")
    args = parser.parse_args(argv)
    try:
        app_version = version(args.inc)
        if args.command == "version":
            print(app_version)
        else:
            commit = args.commit or head_commit(git_runner(args.inc.resolve().parent))
            print(build_tag(app_version, commit))
    except (VersionError, OSError, subprocess.CalledProcessError) as error:
        print(f"cosmoslice_version: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
