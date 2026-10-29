#!/usr/bin/env python3
"""Generate the Cosmyx vendor index (resources/profiles/cosmyx.json) from the profile tree and the built commit.

The index is not tracked in git (D-013): CI writes it before every build, and `just profiles-index` writes it for a
local build. Its version is the UTC committer date of the built commit, `YYYYMMDD.HHMMSS.00.00`, so every build of a
different commit differs in major.minor and the slicer reinstalls the bundled profiles; the same commit gives the
same bytes.

    python3 tools/profiles/cosmyx_index.py generate [--out PATH] [--branch NAME] [--commit SHA] [--commit-date ISO]
    python3 tools/profiles/cosmyx_index.py verify --index PATH [same options]   # regenerate and compare bytes
    python3 tools/profiles/cosmyx_index.py version --commit-date ISO            # print the version only
    python3 tools/profiles/cosmyx_index.py records [--tree PATH] [--out PATH]   # dump the scanned presets

Values not given are read from git (`git log -1 --format=%cI`, `git rev-parse HEAD`, `git rev-parse --abbrev-ref
HEAD`); a detached HEAD needs --branch. Standard library only, Python 3.9 or later (CI runs it on the host runners).
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TREE = REPO_ROOT / "resources" / "profiles" / "cosmyx"
DEFAULT_OUT = REPO_ROOT / "resources" / "profiles" / "cosmyx.json"
DEFAULT_CONFIG = Path(__file__).resolve().parent / "data" / "cosmyx_index.json"

# Top-level folders scanned, with the preset types each one may hold.
FOLDER_TYPES = {"filament": ("filament",), "machine": ("machine_model", "machine"), "process": ("process",)}
LIST_OF_TYPE = {
    "machine_model": "machine_model_list",
    "process": "process_list",
    "filament": "filament_list",
    "machine": "machine_list",
}
# Ordered by inheritance: the loader resolves a parent only if it was loaded earlier in the same list.
INHERITING_LISTS = ("process_list", "filament_list", "machine_list")
CONFIG_KEYS = ("name", "url", "force_update", "machine_model_order", "exclude")
UTC = timezone(timedelta(0))
COMMIT_RE = re.compile(r"^[0-9a-f]{10,64}$")

Runner = Callable[[list], str]


class CosmyxIndexError(ValueError):
    """The tree, the configuration or the git inputs cannot produce a valid index."""


def version_from_commit_date(commit_date: str) -> str:
    """`YYYYMMDD.HHMMSS.00.00` from an ISO 8601 date with a UTC offset, converted to UTC."""
    utc = _utc(commit_date)
    return f"{utc.year:04d}{utc.month:02d}{utc.day:02d}.{utc.hour:02d}{utc.minute:02d}{utc.second:02d}.00.00"


def _utc(commit_date: str) -> datetime:
    text = commit_date.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"  # fromisoformat accepts "Z" only from Python 3.11
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise CosmyxIndexError(f"commit date '{commit_date}' is not ISO 8601") from error
    if parsed.tzinfo is None:
        raise CosmyxIndexError(f"commit date '{commit_date}' has no UTC offset")
    if parsed.microsecond:
        raise CosmyxIndexError(f"commit date '{commit_date}' is not a whole second")
    return parsed.astimezone(UTC)


def scan(tree: Path) -> list[dict]:
    """One record per preset file below machine/, filament/ and process/, sorted by sub_path.

    Names keep their case on disk; dot-files and dot-folders (._*, .smbdelete*, .DS_Store) and non-JSON files are
    skipped, and other top-level folders (I18N/) are not scanned.
    """
    records = []
    for folder in sorted(FOLDER_TYPES):
        base = tree / folder
        for root, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for file in sorted(files):
                if file.startswith(".") or not file.endswith(".json"):
                    continue
                path = Path(root) / file
                sub_path = path.relative_to(tree).as_posix()
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise CosmyxIndexError(f"{sub_path}: cannot read JSON: {error}") from error
                if not isinstance(data, dict):
                    raise CosmyxIndexError(f"{sub_path}: not a JSON object")
                records.append(
                    {
                        "sub_path": sub_path,
                        "name": data.get("name"),
                        "type": data.get("type"),
                        "inherits": data.get("inherits", ""),
                        "instantiation": data.get("instantiation"),
                    }
                )
    return sorted(records, key=lambda r: r["sub_path"])


def load_config(path: Path) -> dict:
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CosmyxIndexError(f"cannot read the configuration {path}: {error}") from error
    missing = [key for key in CONFIG_KEYS if key not in config]
    if missing:
        raise CosmyxIndexError(f"configuration {path} lacks {', '.join(missing)}")
    return config


def build_index(records: list[dict], config: dict, commit_date: str, branch: str, commit: str) -> dict:
    """The vendor index as an ordered dict, from scanned records, the configuration and the built commit."""
    if not branch or branch == "HEAD":
        raise CosmyxIndexError(f"branch '{branch}' is not a branch name")
    if not COMMIT_RE.match(commit):
        raise CosmyxIndexError(f"commit '{commit}' is not a full or abbreviated (10+) lowercase hex SHA")
    utc = _utc(commit_date)
    lists = _classify(_without_exclusions(records, config["exclude"]))
    ordered = {"machine_model_list": _order_models(lists["machine_model_list"], config["machine_model_order"])}
    for key in INHERITING_LISTS:
        ordered[key] = _order_by_inheritance(key, lists[key])
    return {
        "name": config["name"],
        "url": config["url"],
        "version": version_from_commit_date(commit_date),
        "force_update": config["force_update"],
        "description": f"Cosmyx profiles of {branch} at {commit[:10]}, committed {utc:%Y-%m-%dT%H:%M:%SZ}",
        "machine_model_list": _entries(ordered["machine_model_list"]),
        "process_list": _entries(ordered["process_list"]),
        "filament_list": _entries(ordered["filament_list"]),
        "machine_list": _entries(ordered["machine_list"]),
    }


def render(index: dict) -> bytes:
    """UTF-8, four-space indent, LF, trailing newline: the same bytes on every OS."""
    return (json.dumps(index, indent=4, ensure_ascii=False) + "\n").encode("utf-8")


def _without_exclusions(records: list[dict], exclude: list[dict]) -> list[dict]:
    known = {r["sub_path"] for r in records}
    excluded = set()
    for entry in exclude:
        sub_path = entry.get("sub_path", "")
        if not entry.get("reason"):
            raise CosmyxIndexError(f"exclusion '{sub_path}' has no reason")
        if sub_path not in known:
            raise CosmyxIndexError(f"exclusion '{sub_path}' names no preset file (stale entry)")
        excluded.add(sub_path)
    return [r for r in records if r["sub_path"] not in excluded]


def _classify(records: list[dict]) -> dict[str, list[dict]]:
    lists: dict[str, list[dict]] = {key: [] for key in LIST_OF_TYPE.values()}
    names: dict[str, set] = {key: set() for key in LIST_OF_TYPE.values()}
    for record in records:
        sub_path, name, kind = record["sub_path"], record["name"], record["type"]
        folder = sub_path.split("/", 1)[0]
        if not isinstance(name, str) or not name:
            raise CosmyxIndexError(f"{sub_path}: no name")
        if not isinstance(kind, str) or not kind:
            raise CosmyxIndexError(f"{sub_path}: no type")
        if kind not in FOLDER_TYPES.get(folder, ()):
            raise CosmyxIndexError(f"{sub_path}: type '{kind}' does not belong in folder {folder}/")
        if kind != "machine_model" and record["instantiation"] is None:
            raise CosmyxIndexError(f"{sub_path}: no instantiation")
        key = LIST_OF_TYPE[kind]
        if name in names[key]:
            raise CosmyxIndexError(f"{sub_path}: duplicate name '{name}' in {key}")
        names[key].add(name)
        lists[key].append(record)
    return lists


def _order_models(models: list[dict], order: list[str]) -> list[dict]:
    """The configured order first (it is the setup wizard's order), then the other models by name."""
    by_name = {m["name"]: m for m in models}
    for name in order:
        if name not in by_name:
            raise CosmyxIndexError(f"machine_model_order names '{name}', which is no machine model (stale entry)")
    if len(set(order)) != len(order):
        raise CosmyxIndexError("machine_model_order lists a model twice")
    rest = sorted(name for name in by_name if name not in order)
    return [by_name[name] for name in [*order, *rest]]


def _order_by_inheritance(key: str, records: list[dict]) -> list[dict]:
    """Kahn's topological sort, parents first, ties broken by name (as the former ztool_generate_cosmyx_json.py)."""
    by_name = {r["name"]: r for r in records}
    children: dict[str, list[str]] = {name: [] for name in by_name}
    pending: dict[str, int] = {}
    for name, record in by_name.items():
        parent = record["inherits"]
        if parent:
            if parent not in by_name:
                raise CosmyxIndexError(f"{record['sub_path']}: parent '{parent}' is not in {key}")
            children[parent].append(name)
        pending[name] = 1 if parent else 0
    ready = [name for name, count in pending.items() if count == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        name = heapq.heappop(ready)
        ordered.append(by_name[name])
        for child in children[name]:
            pending[child] -= 1
            if pending[child] == 0:
                heapq.heappush(ready, child)
    if len(ordered) != len(records):
        stuck = sorted(name for name, count in pending.items() if count)
        raise CosmyxIndexError(f"inheritance cycle in {key}: {', '.join(stuck)}")
    return ordered


def _entries(records: list[dict]) -> list[dict]:
    return [{"name": r["name"], "sub_path": r["sub_path"]} for r in records]


def git_runner(args: list) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=False
        )
    except OSError as error:
        raise CosmyxIndexError(f"cannot run git: {error}") from error
    if result.returncode != 0:
        raise CosmyxIndexError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _resolve_source(args: argparse.Namespace, runner: Runner) -> tuple[str, str, str]:
    """Commit, commit date and branch: given on the command line, or read from git."""
    commit = args.commit or runner(["rev-parse", "HEAD"])
    commit_date = args.commit_date or runner(["log", "-1", "--format=%cI", commit])
    branch = args.branch or runner(["rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "HEAD":
        raise CosmyxIndexError("HEAD is detached: pass the branch name with --branch")
    return commit, commit_date, branch


def _generate(args: argparse.Namespace, runner: Runner) -> bytes:
    commit, commit_date, branch = _resolve_source(args, runner)
    config = load_config(args.config)
    return render(build_index(scan(args.tree), config, commit_date, branch, commit))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cosmyx_index.py", description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add_source(p: argparse.ArgumentParser) -> None:
        p.add_argument("--tree", type=Path, default=DEFAULT_TREE, help="the Cosmyx profile folder")
        p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="the committed index configuration")
        p.add_argument("--commit-date", help="ISO 8601 committer date with offset (default: git)")
        p.add_argument("--branch", help="branch name for the description (default: git; required on detached HEAD)")
        p.add_argument("--commit", help="commit SHA (default: git rev-parse HEAD)")

    generate = sub.add_parser("generate", help="write the index")
    add_source(generate)
    generate.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output file")
    verify = sub.add_parser("verify", help="regenerate in memory and compare with an existing index, byte for byte")
    add_source(verify)
    verify.add_argument("--index", type=Path, required=True, help="the index to check")
    version = sub.add_parser("version", help="print the version for a commit date")
    version.add_argument("--commit-date", required=True)
    records = sub.add_parser("records", help="dump the scanned presets as JSON (test fixture maker)")
    records.add_argument("--tree", type=Path, default=DEFAULT_TREE)
    records.add_argument("--out", type=Path, help="output file (default: stdout)")
    return parser


def main(argv: list | None = None, runner: Runner | None = None) -> int:
    args = _parser().parse_args(argv)
    runner = runner or git_runner
    try:
        if args.command == "version":
            print(version_from_commit_date(args.commit_date))
        elif args.command == "records":
            data = (json.dumps(scan(args.tree), indent=4, ensure_ascii=False) + "\n").encode("utf-8")
            if args.out:
                args.out.write_bytes(data)
            else:
                sys.stdout.buffer.write(data)
        elif args.command == "generate":
            data = _generate(args, runner)
            args.out.write_bytes(data)
            print(f"cosmyx_index.py: wrote {args.out} ({json.loads(data)['version']})")
        else:
            expected = _generate(args, runner)
            try:
                actual = args.index.read_bytes()
            except OSError as error:
                raise CosmyxIndexError(f"cannot read {args.index}: {error}") from error
            if actual != expected:
                raise CosmyxIndexError(f"{args.index} differs from the index generated for this commit")
            print(f"cosmyx_index.py: {args.index} matches")
    except CosmyxIndexError as error:
        print(f"cosmyx_index.py: error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
