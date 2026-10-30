"""Unit tests of the product-name scanner: token rule, C++ lexer and resource readers."""

from pathlib import Path

import product_name as pn
import pytest


@pytest.mark.parametrize(
    "text",
    [
        "OrcaSlicer",
        "Orca Slicer",
        "Orca will",
        "ORCA",
        "\\nOrca will",
        "(Orca)",
        "restarting Orca.",
        "Orca-PA",
        "Orcslicer",
        "Orc Slicer",
    ],
)
def test_token_matches_product_name(text: str) -> None:
    assert pn.has_token(text)


@pytest.mark.parametrize("text", ["orca_slicer", "orcaslicer.com", "Orcas", "TorcaSlicer", "CosmoSlice", "orca"])
def test_token_ignores_other_words(text: str) -> None:
    assert not pn.has_token(text)


def test_native_tokens() -> None:
    assert pn.has_native_token("逆戟鲸切片", "zh_CN")
    assert pn.has_native_token("오르카 슬라이서", "ko")
    assert not pn.has_native_token("逆戟鲸", "fr")


def raws(source: str) -> list[str]:
    return [lit.raw for lit in pn.iter_literals(source)]


def test_lexer_skips_comments_and_chars() -> None:
    source = """
    // "OrcaSlicer in a line comment"
    /* "OrcaSlicer in a block
       comment" */
    char c = '"'; char d = '\\'';
    auto s = "real";
    """
    assert raws(source) == ["real"]


def test_lexer_digit_separator_is_not_a_char_literal() -> None:
    assert raws("int n = 1'000'000; auto s = \"x\";") == ["x"]


def test_lexer_escaped_quote_and_prefixes() -> None:
    lits = pn.iter_literals('a = L"wide \\"q\\""; b = u8"utf"; c = foo"bar";')
    assert [(lit.prefix, lit.raw) for lit in lits] == [("L", 'wide \\"q\\"'), ("u8", "utf"), ("", "bar")]


def test_lexer_raw_string() -> None:
    lits = pn.iter_literals('auto r = R"js(var x = "Orca"; )js"; auto t = "after";')
    assert [lit.raw for lit in lits] == ['var x = "Orca"; ', "after"]
    assert lits[0].prefix == "R"


def test_lexer_lines_and_context() -> None:
    source = 'int a;\nBOOST_LOG_TRIVIAL(info) << "Orca log";\nshow(_L("Orca text"));\n#include "OrcaSlicer.hpp"\n'
    lits = pn.iter_literals(source, "f.cpp")
    assert [(lit.line, lit.is_log, lit.is_include) for lit in lits] == [
        (2, True, False),
        (3, False, False),
        (4, False, True),
    ]


def test_lexer_log_context_spans_lines() -> None:
    source = 'BOOST_LOG_TRIVIAL(info) << "a"\n    << "Orca b";\nshow("Orca c");'
    assert [lit.is_log for lit in pn.iter_literals(source)] == [True, True, False]


def test_product_literals_filters(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.cpp").write_text(
        '#include "OrcaSlicer.hpp"\nBOOST_LOG_TRIVIAL(info) << "Orca";\nauto t = _L("Orca text");\n', encoding="utf-8"
    )
    (src / "b.txt").write_text('"Orca"', encoding="utf-8")
    found = pn.product_literals(src, tmp_path)
    assert [(lit.path, lit.raw) for lit in found] == [("src/a.cpp", "Orca text")]


def test_hint_texts_decode_escapes(tmp_path: Path) -> None:
    ini = tmp_path / "hints.ini"
    ini.write_text('[hint:A]\ntext = Title\\nSay \\"Orca\\"\n\n[hint:B]\nimage = x.png\n', encoding="utf-8")
    assert pn.hint_texts(ini) == {"hint:A": 'Title\nSay "Orca"'}


def test_text_js_blocks(tmp_path: Path) -> None:
    js = tmp_path / "text.js"
    js.write_text(
        'var LangText = {\n  en: {\n    t1: "Welcome to Orca",\n    t2: "B",\n  },\n  fr: {\n'
        '    t1: "Bienvenue \\"x\\"",\n  },\n};\n',
        encoding="utf-8",
    )
    assert pn.text_js_blocks(js) == {"en": {"t1": "Welcome to Orca", "t2": "B"}, "fr": {"t1": 'Bienvenue \\"x\\"'}}


def test_guide_texts_only_trans_elements(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pn, "REPO_ROOT", tmp_path)
    page = tmp_path / "guide" / "1" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        '<div class="a trans" tid="t1">Welcome to <b>Orca</b><br>Slicer</div>\n'
        '<div class="other">Orca hidden</div>\n<!-- Orca comment -->\n',
        encoding="utf-8",
    )
    assert pn.guide_texts(tmp_path / "guide") == [
        ("guide/1/index.html", 1, "Welcome to"),
        ("guide/1/index.html", 1, "Orca"),
        ("guide/1/index.html", 1, "Slicer"),
    ]


def test_po_language_of_text_js_blocks() -> None:
    langs = {"fr", "zh_CN", "pt_BR", "lt"}
    assert [pn.po_language(b, langs) for b in ["fr_FR", "zh_CN", "pt_BR", "lt"]] == ["fr", "zh_CN", "pt_BR", "lt"]


def test_guide_tids(tmp_path: Path) -> None:
    (tmp_path / "1").mkdir()
    (tmp_path / "1" / "index.html").write_text('<a tid="t1">x</a><b data-tid="no" tid="t2"></b>', encoding="utf-8")
    assert pn.guide_tids(tmp_path) == {"t1", "t2"}


def test_guide_tids_include_keys_injected_by_page_scripts(tmp_path: Path) -> None:
    (tmp_path / "21").mkdir()
    (tmp_path / "21" / "21.js").write_text("""html += '<div class="trans" tid="t11">all</div>';""", encoding="utf-8")
    assert pn.guide_tids(tmp_path) == {"t11"}
