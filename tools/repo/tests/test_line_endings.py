"""Repository hygiene: .gitattributes keeps every text file LF, and the CRLF check looks at tracked files only."""

from pathlib import Path

import line_endings as le

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_gitattributes_forces_lf_and_marks_binaries() -> None:
    lines = {line.strip() for line in (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()}
    assert "* text=auto eol=lf" in lines
    for suffix in le.BINARY_SUFFIXES:
        assert f"*{suffix} binary" in lines


def test_ls_files_output_is_split_on_nul() -> None:
    output = "a.txt\0dir/b c.py\0café.md\0".encode()
    assert le.parse_ls_files(output) == ["a.txt", "dir/b c.py", "café.md"]
    assert le.parse_ls_files(b"") == []


def test_declared_binary_suffixes_are_not_candidates() -> None:
    assert le.text_candidates(["logo.PNG", "a/model.3mf", "src/x.cpp", "justfile"]) == ["src/x.cpp", "justfile"]


def test_only_listed_files_are_checked(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "tracked.sh").write_bytes(b"echo\r\n")
    (tmp_path / "clean.txt").write_bytes(b"ok\n")
    # Not in the tracked list (untracked or ignored): never reported, even with CRLF.
    (tmp_path / "untracked.txt").write_bytes(b"local\r\n")
    (tmp_path / "blob.bin").write_bytes(b"\0\r\n")
    listed = ["sub/tracked.sh", "clean.txt", "blob.bin", "deleted.txt"]
    assert le.crlf_offenders(tmp_path, listed) == ["sub/tracked.sh"]


def test_main_reports_tracked_crlf(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "a.txt").write_bytes(b"x\r\n")
    monkeypatch.setattr(le, "tracked_files", lambda root: ["a.txt"])
    assert le.main(tmp_path) == 1
    assert "a.txt" in capsys.readouterr().err


def test_main_fails_clearly_without_git(tmp_path: Path, monkeypatch, capsys) -> None:
    def no_git(root: Path) -> list[str]:
        raise FileNotFoundError("git")

    monkeypatch.setattr(le, "tracked_files", no_git)
    assert le.main(tmp_path) == 2
    assert "git" in capsys.readouterr().err
