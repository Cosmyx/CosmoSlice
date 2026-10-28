"""Tests of the translator status report."""

from pathlib import Path

import status

PO = """msgid ""
msgstr ""

#, fuzzy
#| msgid "Orca A"
msgid "CosmoSlice A"
msgstr "Orca A fr"

msgid "Other"
msgstr "Autre Orca Slicer"

msgid "Kept Orca"
msgstr "Garde Orca"

msgid "Clean"
msgstr "Propre"
"""


def test_language_status(tmp_path: Path) -> None:
    path = tmp_path / "fr" / "x_fr.po"
    path.parent.mkdir()
    path.write_text(PO, encoding="utf-8")
    result = status.language_status(path, renamed={"CosmoSlice A"}, kept={"Kept Orca"})
    assert result == {"fuzzy": ["CosmoSlice A"], "stray": ["Other"]}


def test_main_reports_every_language(capsys) -> None:
    assert status.main([]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 20 and out[0].startswith("ca: ")


def test_unknown_language_fails() -> None:
    assert status.main(["xx"]) == 2
