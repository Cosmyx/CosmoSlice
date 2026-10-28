"""Tests of the in-place msgid rename tool (D-004)."""

import json
from pathlib import Path

import pytest
import rename_msgids as rm

MAPPING = [
    {"old": "OrcaSlicer is great", "new": "CosmoSlice is great"},
    {
        "old": "OrcaSlicer will terminate because of a localization error. It will be appreciated if you report "
        "the specific scenario this issue happened.",
        "new": "CosmoSlice will terminate because of a localization error. It will be appreciated if you report "
        "the specific scenario this issue happened.",
    },
]

POT = """# header
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: Orca Slicer\\n"

msgid "Before"
msgstr ""

msgid "OrcaSlicer is great"
msgstr ""

msgid ""
"OrcaSlicer will terminate because of a localization error. It will be "
"appreciated if you report the specific scenario this issue happened."
msgstr ""
"""

PO = """msgid ""
msgstr ""
"Project-Id-Version: Orca Slicer\\n"
"Language: fr\\n"

msgid "Before"
msgstr "Avant"

#: src/a.cpp:3
#, boost-format
msgid "OrcaSlicer is great"
msgstr "Orca Slicer est génial"

msgid ""
"OrcaSlicer will terminate because of a localization error. It will be "
"appreciated if you report the specific scenario this issue happened."
msgstr ""

#~ msgid "OrcaSlicer is great"
#~ msgstr "obsolete"
"""

PO_EXPECTED = """msgid ""
msgstr ""
"Project-Id-Version: Orca Slicer\\n"
"Language: fr\\n"

msgid "Before"
msgstr "Avant"

#: src/a.cpp:3
#, fuzzy, boost-format
#| msgid "OrcaSlicer is great"
msgid "CosmoSlice is great"
msgstr "Orca Slicer est génial"

msgid ""
"CosmoSlice will terminate because of a localization error. It will be "
"appreciated if you report the specific scenario this issue happened."
msgstr ""

#~ msgid "OrcaSlicer is great"
#~ msgstr "obsolete"
"""


def pairs(raw: list[dict[str, str]] = MAPPING) -> list[rm.Pair]:
    return rm.load_mapping_data(raw)


def test_pot_rename_in_place_without_fuzzy() -> None:
    result = rm.rename_text(POT, pairs())
    assert result.renamed == 2
    assert result.text == POT.replace("OrcaSlicer is great", "CosmoSlice is great").replace(
        '"OrcaSlicer will', '"CosmoSlice will'
    )
    assert "#|" not in result.text


def test_po_translated_entry_gets_fuzzy_and_previous_msgid() -> None:
    result = rm.rename_text(PO, pairs())
    assert result.text == PO_EXPECTED
    assert result.fuzzied == 1


def test_untranslated_entry_without_flags_gets_plain_fuzzy_line() -> None:
    text = 'msgid "OrcaSlicer is great"\nmsgstr "Super"\n'
    out = rm.rename_text(text, pairs(MAPPING[:1])).text
    assert out == '#, fuzzy\n#| msgid "OrcaSlicer is great"\nmsgid "CosmoSlice is great"\nmsgstr "Super"\n'


def test_already_fuzzy_entry_keeps_its_previous_msgid() -> None:
    text = '#, fuzzy\n#| msgid "Orca is great"\nmsgid "OrcaSlicer is great"\nmsgstr "Super"\n'
    out = rm.rename_text(text, pairs(MAPPING[:1])).text
    assert out == '#, fuzzy\n#| msgid "Orca is great"\nmsgid "CosmoSlice is great"\nmsgstr "Super"\n'


def test_plural_entry_translated_in_one_form_is_fuzzied() -> None:
    raw = [{"old": "Orca file", "new": "CosmoSlice file"}]
    text = 'msgid "Orca file"\nmsgid_plural "files"\nmsgstr[0] ""\nmsgstr[1] "x"\n'
    out = rm.rename_text(text, pairs(raw)).text
    assert out.startswith('#, fuzzy\n#| msgid "Orca file"\nmsgid "CosmoSlice file"\n')


def test_idempotent() -> None:
    once = rm.rename_text(PO, pairs()).text
    again = rm.rename_text(once, pairs())
    assert again.text == once
    assert again.renamed == 0


def test_missing_old_and_new_fails() -> None:
    with pytest.raises(rm.RenameError, match="neither"):
        rm.rename_text('msgid "Other"\nmsgstr ""\n', pairs(MAPPING[:1]))


def test_new_msgid_already_present_fails() -> None:
    text = 'msgid "OrcaSlicer is great"\nmsgstr ""\n\nmsgid "CosmoSlice is great"\nmsgstr ""\n'
    with pytest.raises(rm.RenameError, match="already exists"):
        rm.rename_text(text, pairs(MAPPING[:1]))


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([{"old": "a", "new": "a"}], "identical"),
        ([{"old": "a", "new": "c"}, {"old": "b", "new": "c"}], "duplicate new"),
        ([{"old": "a", "new": "c"}, {"old": "a", "new": "d"}], "duplicate old"),
        ([{"old": "a", "new": "b"}, {"old": "b", "new": "c"}], "chain"),
        ([{"old": "a"}], "old and new"),
    ],
)
def test_invalid_mapping_fails(raw: list[dict[str, str]], message: str) -> None:
    with pytest.raises(rm.RenameError, match=message):
        rm.load_mapping_data(raw)


def test_files_are_rewritten_lf_and_discovered(tmp_path: Path) -> None:
    catalogs = tmp_path / "i18n"
    (catalogs / "fr").mkdir(parents=True)
    (catalogs / "OrcaSlicer.pot").write_bytes(POT.encode("utf-8"))
    (catalogs / "fr" / "OrcaSlicer_fr.po").write_bytes(PO.encode("utf-8"))
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps(MAPPING), encoding="utf-8")

    assert rm.main(["--mapping", str(mapping), "--catalogs", str(catalogs), "--check"]) == 1
    assert rm.main(["--mapping", str(mapping), "--catalogs", str(catalogs)]) == 0
    data = (catalogs / "fr" / "OrcaSlicer_fr.po").read_bytes()
    assert data == PO_EXPECTED.encode("utf-8")
    assert b"\r" not in data
    assert rm.main(["--mapping", str(mapping), "--catalogs", str(catalogs), "--check"]) == 0


def test_catalogue_discovery_order(tmp_path: Path) -> None:
    for rel in ["b/x_b.po", "a/x_a.po", "x.pot"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("", encoding="utf-8")
    assert [p.relative_to(tmp_path).as_posix() for p in rm.discover_catalogs(tmp_path)] == [
        "x.pot",
        "a/x_a.po",
        "b/x_b.po",
    ]
