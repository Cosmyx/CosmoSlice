#!/usr/bin/env python3
"""Run a command in one of the repository's pinned Docker images.

Every containerised step (tests, lint, i18n checks, asset rendering) goes through this launcher, so the
image, platform and mounts are the same on macOS, Linux and Windows hosts.

    python3 tools/docker/run.py [--image ci] [--workdir scripts/foo] -- <command> [args...]
    python3 tools/docker/run.py [--image ci] --build-only

The image is built from tools/docker/<image>/ and tagged with a hash of that build context, so editing the
Dockerfile (or a file it copies) rebuilds it, and an unchanged context reuses the local image. Builds and runs
always use linux/amd64, the platform of CI, so rendering and tool output are identical on every host.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

PLATFORM = "linux/amd64"
MOUNT_POINT = "/repo"
IMAGE_PREFIX = "cosmoslice-"
REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = Path(__file__).resolve().parent


def context_dir(image: str, images_dir: Path = IMAGES_DIR) -> Path:
    """Return the build context folder of an image, failing clearly when it does not exist."""
    folder = images_dir / image
    if not (folder / "Dockerfile").is_file():
        raise SystemExit(f"run.py: no Dockerfile for image '{image}' in {folder}")
    return folder


def context_hash(folder: Path) -> str:
    """Hash every file of the build context (relative POSIX path + bytes), independent of the host OS."""
    digest = hashlib.sha256()
    files = sorted(
        (p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts),
        key=lambda p: p.relative_to(folder).as_posix(),
    )
    for path in files:
        digest.update(path.relative_to(folder).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def image_tag(image: str, folder: Path) -> str:
    """Local tag of an image: its name plus the hash of its build context."""
    return f"{IMAGE_PREFIX}{image}:{context_hash(folder)}"


def build_command(tag: str, folder: Path) -> list[str]:
    """docker build command for an image context."""
    return ["docker", "build", "--platform", PLATFORM, "--tag", tag, str(folder)]


def user_args() -> list[str]:
    """Run as the host user where the host has POSIX ids, so files written in the mount keep their owner."""
    getuid = getattr(os, "getuid", None)
    getgid = getattr(os, "getgid", None)
    if getuid is None or getgid is None:
        return []
    return ["--user", f"{getuid()}:{getgid()}"]


def container_workdir(workdir: str | None) -> str:
    """Working directory inside the container: the mount point, or a repository-relative folder below it."""
    if not workdir:
        return MOUNT_POINT
    relative = Path(workdir)
    if relative.is_absolute():
        relative = relative.resolve().relative_to(REPO_ROOT)
    return str(PurePosixPath(MOUNT_POINT, *relative.parts))


def run_command(
    tag: str,
    command: list[str],
    repo_root: Path = REPO_ROOT,
    workdir: str | None = None,
    user: list[str] | None = None,
    interactive: bool = False,
) -> list[str]:
    """docker run command that mounts the repository at /repo and runs `command` there."""
    args = ["docker", "run", "--rm", "--platform", PLATFORM]
    if interactive:
        args.append("-it")
    args += ["--mount", f"type=bind,source={repo_root},target={MOUNT_POINT}"]
    args += ["--workdir", container_workdir(workdir)]
    args += ["--env", "HOME=/tmp"]
    args += user_args() if user is None else user
    args.append(tag)
    args += command
    return args


def image_exists(tag: str) -> bool:
    """True when the tagged image is already present locally."""
    result = subprocess.run(
        ["docker", "image", "inspect", tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    return result.returncode == 0


def ensure_image(image: str) -> str:
    """Build the image if its current context has not been built yet, and return its tag."""
    folder = context_dir(image)
    tag = image_tag(image, folder)
    if not image_exists(tag):
        subprocess.run(build_command(tag, folder), check=True)
    return tag


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", default="ci", help="image folder under tools/docker/ (default: ci)")
    parser.add_argument("--workdir", help="repository-relative working directory inside the container")
    parser.add_argument("--build-only", action="store_true", help="build the image if needed, print its tag")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command to run, after --")
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.build_only and not args.command:
        parser.error("a command is required (after --), or --build-only")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    tag = ensure_image(args.image)
    if args.build_only:
        print(tag)
        return 0
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    command = run_command(tag, args.command, workdir=args.workdir, interactive=interactive)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
