"""Tests of the byte-preserving PO reader and the gettext-style field renderer."""

import po
import pytest

SAMPLE = """# header comment
msgid ""
msgstr ""
"Language: fr\\n"

#: src/a.cpp:1
#, c-format
msgid "Hello %s"
msgstr "Bonjour %s"

msgctxt "menu"
msgid ""
"Two\\n"
"lines"
msgstr ""

msgid "one"
msgid_plural "many"
msgstr[0] "un"
msgstr[1] "plusieurs"

#~ msgid "gone"
#~ msgstr "parti"
"""


def test_parse_entries_and_spans() -> None:
    lines, entries = po.parse(SAMPLE)
    assert [e.msgid for e in entries] == ["", "Hello %s", "Two\nlines", "one", "gone"]
    header, hello, two, plural, gone = entries
    assert header.is_header and not hello.is_header
    assert hello.flags == ["c-format"] and hello.translated and not hello.is_fuzzy
    assert two.msgctxt == "menu" and not two.translated
    msgid = two.get("msgid")
    assert lines[msgid.start : msgid.end] == ['msgid ""', '"Two\\n"', '"lines"']
    assert plural.msgstrs == ["un", "plusieurs"]
    assert gone.obsolete
    assert po.active_entries(entries) == [hello, two, plural]


def test_quote_roundtrip() -> None:
    text = 'a "b" \\ c\n\td'
    assert po.unquote('"' + po.quote(text) + '"') == text
    assert po.unquote('"\\101"') == "A"


def test_render_short_field_on_one_line() -> None:
    assert po.render_field("msgid", "Hello") == ['msgid "Hello"']
    assert po.render_field("msgid", "End\n") == ['msgid "End\\n"']
    assert po.render_field("msgid", "x", prefix="#| ") == ['#| msgid "x"']


def test_render_inner_newline_splits_lines() -> None:
    assert po.render_field("msgid", "a\nb") == ['msgid ""', '"a\\n"', '"b"']


def test_render_wraps_at_79_after_spaces() -> None:
    text = "word " * 30
    lines = po.render_field("msgid", text.strip())
    assert lines[0] == 'msgid ""'
    assert all(len(line) <= 79 for line in lines)
    assert "".join(po.unquote(line) for line in lines[1:]) == text.strip()


def test_render_matches_gettext_layout() -> None:
    value = (
        "OrcaSlicer will terminate because of a localization error. It will be appreciated if you report the "
        "specific scenario this issue happened."
    )
    assert po.render_field("msgid", value) == [
        'msgid ""',
        '"OrcaSlicer will terminate because of a localization error. It will be "',
        '"appreciated if you report the specific scenario this issue happened."',
    ]


def test_crlf_is_rejected() -> None:
    with pytest.raises(ValueError, match="LF"):
        po.parse('msgid "a"\r\nmsgstr ""\r\n')


def test_unexpected_line_is_an_error() -> None:
    with pytest.raises(ValueError, match="line 2"):
        po.parse('msgid "a"\ngarbage\nmsgstr ""\n')


def test_entries_without_blank_line_between_them_are_split() -> None:
    text = 'msgid "a"\nmsgstr ""\nmsgid "b"\nmsgstr "B"\n#, fuzzy\nmsgid "c"\nmsgstr ""\n'
    lines, entries = po.parse(text)
    assert [e.msgid for e in entries] == ["a", "b", "c"]
    assert entries[1].msgstrs == ["B"]
    assert entries[2].is_fuzzy
    assert (entries[2].start, entries[2].end) == (4, 7)
