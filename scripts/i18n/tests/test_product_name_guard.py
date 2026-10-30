"""Guards of the CosmoSlice rename (D-001, D-006): no user-visible text names the upstream product any more, except
the entries kept on purpose in data/product_name_allowlist.json, and the catalogues follow the frozen mapping."""

import sys
from collections import Counter
from functools import cache
from pathlib import Path

import po
import product_name as pn
import pytest

sys.path.insert(0, str(pn.REPO_ROOT / "scripts"))
import update_pot


@cache
def source_msgids() -> frozenset[tuple[str | None, str, str | None]]:
    keys = set()
    for path in update_pot.collect_source_files(pn.SRC_DIR, None):
        keys |= {e.key for e in update_pot.extract_from_file(path)}
    return frozenset(keys)


@cache
def catalog(path: Path) -> tuple[po.Entry, ...]:
    _, entries = po.parse(path.read_text(encoding="utf-8"))
    return tuple(po.active_entries(entries))


def po_files() -> list[Path]:
    return sorted(pn.CATALOG_DIR.glob("*/*.po"), key=lambda p: p.as_posix())


ALLOWLIST = pn.load_allowlist()
KEPT_MSGIDS = {item["msgid"] for item in ALLOWLIST["msgids"]}
MAPPING = pn.load_mapping()
REASON_CATEGORIES = {
    "asset", "cli", "compared", "credit", "dev-tool", "external", "internal", "kept-name", "linux-desktop",
    "persisted", "url",
}  # fmt: skip


def test_allowlist_entries_have_a_known_reason() -> None:
    for item in ALLOWLIST["msgids"] + ALLOWLIST["cpp_literals"]:
        assert item["reason"].split(":", 1)[0] in REASON_CATEGORIES, item


def test_g1_source_msgids_do_not_name_the_upstream_product() -> None:
    named = {msgid for _, msgid, _ in source_msgids() if pn.has_token(msgid)}
    assert sorted(named - KEPT_MSGIDS) == []
    assert sorted(KEPT_MSGIDS - named) == [], "stale allow-list msgids"


def test_g2_cpp_literals_do_not_name_the_upstream_product() -> None:
    found = Counter((lit.path, lit.raw) for lit in pn.product_literals())
    allowed = Counter({(item["path"], item["literal"]): item["count"] for item in ALLOWLIST["cpp_literals"]})
    unexpected = {key: n - allowed[key] for key, n in found.items() if n > allowed[key]}
    stale = {key: n - found[key] for key, n in allowed.items() if n > found[key]}
    assert unexpected == {}, "new user-visible literal names the upstream product (rename it or allow-list it)"
    assert stale == {}, "stale allow-list entries (remove them or fix the count)"


def test_g3_pot_msgids_do_not_name_the_upstream_product() -> None:
    named = {e.msgid for e in catalog(pn.POT_PATH) if pn.has_token(e.msgid)}
    assert sorted(named - KEPT_MSGIDS) == []


def test_g4_every_source_msgid_and_hint_is_in_the_pot() -> None:
    pot = {(e.msgctxt, e.msgid) for e in catalog(pn.POT_PATH)}
    missing = sorted(msgid for ctx, msgid, _ in source_msgids() if (ctx, msgid) not in pot)
    missing += sorted(text for text in pn.hint_texts().values() if (None, text) not in pot)
    assert missing == []


def test_g5_hints_do_not_name_the_upstream_product() -> None:
    assert {k: v for k, v in pn.hint_texts().items() if pn.has_token(v)} == {}


@pytest.mark.parametrize("path", po_files(), ids=lambda p: p.parent.name)
def test_g8_confirmed_translations_of_renamed_msgids_use_the_new_name(path: Path) -> None:
    lang = path.parent.name
    renamed = {pair["new"] for pair in MAPPING}
    stale = [
        e.msgid
        for e in catalog(path)
        if e.msgid in renamed
        and not e.is_fuzzy
        and any(pn.has_token(s) or pn.has_native_token(s, lang) for s in e.msgstrs)
    ]
    assert stale == []


@pytest.mark.parametrize(
    "path", [pn.POT_PATH, *po_files()], ids=lambda p: p.parent.name if p.suffix == ".po" else "pot"
)
def test_g9_catalogue_follows_the_mapping(path: Path) -> None:
    msgids = {e.msgid for e in catalog(path)}
    assert [pair["new"] for pair in MAPPING if pair["new"] not in msgids] == []
    assert [pair["old"] for pair in MAPPING if pair["old"] in msgids] == []


def test_mapping_is_the_frozen_contract() -> None:
    assert len(MAPPING) == 76
    assert all(pn.NEW_NAME in pair["new"] for pair in MAPPING)
    assert all(not pn.has_token(pair["new"]) or pair["new"] in KEPT_MSGIDS for pair in MAPPING)


def test_g6_text_js_english_block_does_not_name_the_upstream_product() -> None:
    english = pn.text_js_blocks()["en"]
    assert {k: v for k, v in english.items() if pn.has_token(v)} == {}


def test_g6_text_js_guide_keys_do_not_name_the_upstream_product_in_any_language() -> None:
    assert pn.stale_text_js_keys() == {}


def test_g7_setup_guide_pages_do_not_name_the_upstream_product() -> None:
    assert [(path, line, text) for path, line, text in pn.guide_texts() if pn.has_token(text)] == []
