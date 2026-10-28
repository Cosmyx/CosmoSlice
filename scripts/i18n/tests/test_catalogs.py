"""Every catalogue compiles with msgfmt --check-format and has no duplicate msgid."""

from pathlib import Path

import check_catalogs
import pytest
from rename_msgids import DEFAULT_CATALOGS


def test_repository_catalogues_are_valid() -> None:
    assert check_catalogs.check(DEFAULT_CATALOGS) == []


def test_missing_msgfmt_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_catalogs.shutil, "which", lambda _: None)
    assert check_catalogs.check(tmp_path)[0].startswith("msgfmt not found")


def test_duplicates_are_reported() -> None:
    text = 'msgid "a"\nmsgstr ""\n\nmsgid "a"\nmsgstr ""\n\nmsgctxt "x"\nmsgid "a"\nmsgstr ""\n'
    assert check_catalogs.duplicate_msgids(text) == ["a"]


def test_broken_format_is_reported(tmp_path: Path) -> None:
    (tmp_path / "fr").mkdir()
    (tmp_path / "fr" / "x_fr.po").write_text(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        '#, c-format\nmsgid "%s files"\nmsgstr "%d fichiers"\n',
        encoding="utf-8",
    )
    problems = check_catalogs.check(tmp_path)
    assert problems and problems[0].startswith("fr/x_fr.po")
