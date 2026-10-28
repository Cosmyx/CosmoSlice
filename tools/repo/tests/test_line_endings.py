"""Repository hygiene: every text file is LF in the working tree, and .gitattributes keeps it that way."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Binary types declared in .gitattributes; they are never checked for line endings.
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".icns",
    ".3mf",
    ".stl",
    ".ttf",
    ".xlsx",
    ".dll",
    ".lib",
    ".exe",
}
# Generated or local folders that are not part of the repository content.
SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".flatpak-builder", "DL_CACHE"}


def is_skipped_dir(path: Path) -> bool:
    name = path.name
    return (
        name in SKIPPED_DIRS or name.startswith(".smbdelete") or (path.parent == REPO_ROOT and name.startswith("build"))
    )


def text_files(root: Path):
    stack = [root]
    while stack:
        folder = stack.pop()
        for entry in folder.iterdir():
            if entry.is_dir():
                if not is_skipped_dir(entry):
                    stack.append(entry)
            elif (
                entry.is_file()
                and entry.suffix.lower() not in BINARY_SUFFIXES
                and not entry.name.startswith(".smbdelete")
            ):
                yield entry


def test_gitattributes_forces_lf_and_marks_binaries() -> None:
    lines = {line.strip() for line in (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()}
    assert "* text=auto eol=lf" in lines
    for suffix in BINARY_SUFFIXES:
        assert f"*{suffix} binary" in lines


def test_no_crlf_in_text_files() -> None:
    offenders = []
    for path in text_files(REPO_ROOT):
        data = path.read_bytes()
        if b"\0" in data[:8000]:
            continue  # binary content with an unusual suffix
        if b"\r\n" in data:
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert offenders == [], f"CRLF line endings in: {offenders[:20]}"
