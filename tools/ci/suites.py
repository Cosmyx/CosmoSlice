#!/usr/bin/env python3
"""Discover the repository's Python test suites and module check recipes.

A suite is any `scripts/<name>/tests` or `tools/<name>/tests` folder; a module check is the `check` recipe of
any `scripts/<name>/justfile` or `tools/<name>/justfile`. Nothing is listed by hand: adding the folder or the
recipe is enough for `just test` and `just ci` to pick it up.

    python3 tools/ci/suites.py list                  # suite names
    python3 tools/ci/suites.py pytest [suite] [-- pytest args]   # run pytest on one suite, or all
    python3 tools/ci/suites.py checks --just <just>  # run every module `check` recipe
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PARENTS = ("scripts", "tools")


def discover_suites(root: Path = REPO_ROOT) -> dict[str, Path]:
    """Map each suite name to its tests folder (repository-relative). Two modules may not share a name."""
    suites: dict[str, Path] = {}
    for parent in MODULE_PARENTS:
        base = root / parent
        if not base.is_dir():
            continue
        for module in sorted(base.iterdir(), key=lambda p: p.name):
            tests = module / "tests"
            if not tests.is_dir():
                continue
            if module.name in suites:
                raise SystemExit(f"suites.py: suite name '{module.name}' exists twice: {suites[module.name]}, {tests}")
            suites[module.name] = tests.relative_to(root)
    return suites


def discover_module_justfiles(root: Path = REPO_ROOT) -> list[Path]:
    """Every module justfile below scripts/ and tools/, in a stable order."""
    found: list[Path] = []
    for parent in MODULE_PARENTS:
        base = root / parent
        if not base.is_dir():
            continue
        found += sorted((m / "justfile" for m in base.iterdir() if (m / "justfile").is_file()), key=str)
    return found


def recipe_names(summary: str) -> set[str]:
    """Parse the output of `just --summary` (space-separated recipe names)."""
    return set(summary.split())


def select_suites(suites: dict[str, Path], name: str | None) -> list[Path]:
    """Folders to run: one named suite, or every suite when no name is given."""
    if not name:
        return [suites[k] for k in sorted(suites)]
    if name not in suites:
        known = ", ".join(sorted(suites)) or "none"
        raise SystemExit(f"suites.py: unknown suite '{name}' (known: {known})")
    return [suites[name]]


def run_pytest(name: str | None, extra: list[str]) -> int:
    paths = [p.as_posix() for p in select_suites(discover_suites(), name)]
    return subprocess.run([sys.executable, "-m", "pytest", *paths, *extra], cwd=REPO_ROOT, check=False).returncode


def run_checks(just: str) -> int:
    status = 0
    for justfile in discover_module_justfiles():
        summary = subprocess.run(
            [just, "--justfile", str(justfile), "--summary"], capture_output=True, text=True, check=True
        ).stdout
        if "check" not in recipe_names(summary):
            continue
        print(f"==> {justfile.relative_to(REPO_ROOT).as_posix()}: check", flush=True)
        result = subprocess.run([just, "--justfile", str(justfile), "check"], check=False)
        status = status or result.returncode
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("list", help="print the suite names")
    pytest_parser = sub.add_parser("pytest", help="run pytest on one suite or all")
    pytest_parser.add_argument("suite", nargs="?", default="")
    pytest_parser.add_argument("extra", nargs=argparse.REMAINDER)
    checks_parser = sub.add_parser("checks", help="run every module check recipe")
    checks_parser.add_argument("--just", default="just", help="just executable")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.mode == "list":
        for name in sorted(discover_suites()):
            print(name)
        return 0
    if args.mode == "pytest":
        extra = args.extra[1:] if args.extra[:1] == ["--"] else args.extra
        return run_pytest(args.suite or None, extra)
    return run_checks(args.just)


if __name__ == "__main__":
    sys.exit(main())
