"""Find the upstream product name (OrcaSlicer, Orca Slicer, Orca, ORCA) in user-visible text (D-001, D-006).

The guard tests use these readers to make sure no user-visible string still names the upstream product, except the
entries kept on purpose in `data/product_name_allowlist.json`:

- C++ sources: a small lexer that returns every string literal with its line and statement context (comments, raw
  strings, character literals and digit separators are handled); log statements are recognised by their context.
- gettext catalogues (via `po`), `resources/data/hints.ini`, the `en` block of `resources/web/data/text.js` and the
  translatable elements of the setup-guide HTML pages.
"""

from __future__ import annotations

import configparser
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from po import unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
CATALOG_DIR = REPO_ROOT / "localization" / "i18n"
POT_PATH = CATALOG_DIR / "OrcaSlicer.pot"
HINTS_PATH = REPO_ROOT / "resources" / "data" / "hints.ini"
TEXT_JS_PATH = REPO_ROOT / "resources" / "web" / "data" / "text.js"
GUIDE_DIR = REPO_ROOT / "resources" / "web" / "guide"
DATA_DIR = Path(__file__).resolve().parent / "data"
MAPPING_PATH = DATA_DIR / "cosmoslice_rename.json"
ALLOWLIST_PATH = DATA_DIR / "product_name_allowlist.json"

CPP_SUFFIXES = {".cpp", ".hpp", ".h", ".mm", ".c", ".cc", ".cxx", ".hxx"}
NEW_NAME = "CosmoSlice"

# The upstream name as a word. It may follow an escaped newline ("\nOrca" in a C++ or PO literal), and lowercase
# identifiers (orca_slicer, orcaslicer.com) never match.
TOKEN = re.compile(r"(?:(?<![A-Za-z])|(?<=\\n))(?:Orca ?Slicer|Orca|ORCA)(?![a-z])")
# Native spellings used by some translations for the upstream name.
NATIVE_TOKENS = {"zh_CN": re.compile("逆戟鲸"), "zh_TW": re.compile("逆戟鯨|逆戟鲸"), "ko": re.compile("오르카")}
LOG_MARKERS = ("BOOST_LOG_TRIVIAL", "COSMO_LOG")


def has_token(text: str) -> bool:
    return TOKEN.search(text) is not None


def has_native_token(text: str, lang: str) -> bool:
    pattern = NATIVE_TOKENS.get(lang)
    return bool(pattern and pattern.search(text))


# ---------------------------------------------------------------------------------------------------------------------
# C++ lexer


@dataclass(frozen=True)
class Literal:
    """One C++ string literal: its raw source text between the quotes, prefix, line and statement context."""

    path: str
    line: int
    prefix: str
    raw: str
    context: str

    @property
    def is_log(self) -> bool:
        return any(marker in self.context for marker in LOG_MARKERS)

    @property
    def is_include(self) -> bool:
        return re.match(r"\s*#\s*(?:include|import)\b", self.context) is not None


_RAW_START = re.compile(r'(?:u8|[uUL])?R"([^()\\\s]{0,16})\(')
_PREFIX = re.compile(r"(?:u8|[uUL])$")
_IDENT_CHAR = re.compile(r"[0-9A-Za-z_]")


def iter_literals(source: str, path: str = "") -> list[Literal]:
    """Return every string literal of a C++ source, skipping comments and character literals."""
    literals: list[Literal] = []
    i = 0
    n = len(source)
    line = 1
    statement_start = 0
    directive_start: int | None = None
    at_line_start = True

    def context_until(end: int) -> str:
        start = directive_start if directive_start is not None else statement_start
        return source[start:end]

    while i < n:
        ch = source[i]
        if ch == "\n":
            line += 1
            if directive_start is not None and source[max(0, i - 1)] != "\\":
                directive_start = None
                statement_start = i + 1
            at_line_start = True
            i += 1
            continue
        if at_line_start and ch == "#":
            directive_start = i
        if not ch.isspace():
            at_line_start = False
        if source.startswith("//", i):
            end = source.find("\n", i)
            i = n if end < 0 else end
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            end = n if end < 0 else end + 2
            line += source.count("\n", i, end)
            i = end
            continue
        if ch in ";{}" and directive_start is None:
            statement_start = i + 1
            i += 1
            continue
        raw = _RAW_START.match(source, i) if ch in "uULR" else None
        if raw and (i == 0 or not _IDENT_CHAR.match(source[i - 1])):
            delimiter = ")" + raw.group(1) + '"'
            body_start = raw.end()
            end = source.find(delimiter, body_start)
            end = n if end < 0 else end
            prefix = source[i : source.index('"', i)]
            literals.append(Literal(path, line, prefix, source[body_start:end], context_until(i)))
            line += source.count("\n", i, end)
            i = end + len(delimiter)
            continue
        if ch == '"':
            j = i + 1
            while j < n and source[j] != '"':
                if source[j] == "\\":
                    j += 1
                elif source[j] == "\n":
                    break
                j += 1
            prefix_match = _PREFIX.search(source, max(0, i - 2), i)
            prefix = prefix_match.group(0) if prefix_match else ""
            if prefix and i - len(prefix) > 0 and _IDENT_CHAR.match(source[i - len(prefix) - 1]):
                prefix = ""
            literals.append(Literal(path, line, prefix, source[i + 1 : j], context_until(i - len(prefix))))
            line += source.count("\n", i, j)
            i = j + 1
            continue
        if ch == "'":
            k = i
            while k > 0 and re.match(r"[0-9A-Za-z_'.]", source[k - 1]):
                k -= 1
            if k < i and source[k].isdigit():
                i += 1  # digit separator, e.g. 1'000
                continue
            j = i + 1
            while j < n and source[j] != "'":
                if source[j] == "\\":
                    j += 1
                elif source[j] == "\n":
                    break
                j += 1
            i = j + 1
            continue
        i += 1
    return literals


def cpp_files(root: Path = SRC_DIR) -> list[Path]:
    return sorted((p for p in root.rglob("*") if p.suffix in CPP_SUFFIXES and p.is_file()), key=lambda p: p.as_posix())


def product_literals(root: Path = SRC_DIR, repo_root: Path = REPO_ROOT) -> list[Literal]:
    """Every non-log, non-include C++ literal below `root` that names the upstream product."""
    found: list[Literal] = []
    for path in cpp_files(root):
        rel = path.relative_to(repo_root).as_posix()
        source = path.read_bytes().decode("utf-8", errors="replace")
        found += [
            lit for lit in iter_literals(source, rel) if has_token(lit.raw) and not lit.is_log and not lit.is_include
        ]
    return found


# ---------------------------------------------------------------------------------------------------------------------
# Data files


def load_mapping(path: Path = MAPPING_PATH) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_allowlist(path: Path = ALLOWLIST_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hint_texts(path: Path = HINTS_PATH) -> dict[str, str]:
    """Hint section -> text, with its escapes (\\n, \\") decoded the way the pot carries it."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(path.read_text(encoding="utf-8"))
    return {s: unquote('"' + parser[s]["text"] + '"') for s in parser.sections() if parser[s].get("text")}


_JS_BLOCK = re.compile(r"^\s{1,8}([A-Za-z_]+)\s*:\s*\{\s*$")
_JS_ENTRY = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def text_js_blocks(path: Path = TEXT_JS_PATH) -> dict[str, dict[str, str]]:
    """Language block -> {key: raw string} of `var LangText = { en: { t1: "..." }, ... }`."""
    blocks: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").split("\n"):
        block = _JS_BLOCK.match(line)
        if block:
            current = block.group(1)
            blocks[current] = {}
            continue
        entry = _JS_ENTRY.match(line)
        if entry and current is not None:
            blocks[current][entry.group(1)] = entry.group(2)
    return blocks


class _TransParser(HTMLParser):
    """Collect the text of elements whose class list contains `trans` (the fallback text of guide pages)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[bool] = []
        self.texts: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = next((v or "" for k, v in attrs if k == "class"), "").split()
        if tag in {"br", "img", "input", "meta", "link", "hr"}:
            return
        self.stack.append("trans" in classes or (bool(self.stack) and self.stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"br", "img", "input", "meta", "link", "hr"}:
            return
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.stack and self.stack[-1] and data.strip():
            self.texts.append((self.getpos()[0], data.strip()))


def guide_texts(root: Path = GUIDE_DIR) -> list[tuple[str, int, str]]:
    """(path, line, text) of every translatable element of every setup-guide page."""
    out: list[tuple[str, int, str]] = []
    for page in sorted(root.rglob("*.html"), key=lambda p: p.as_posix()):
        parser = _TransParser()
        parser.feed(page.read_text(encoding="utf-8"))
        rel = page.relative_to(REPO_ROOT).as_posix()
        out += [(rel, line, text) for line, text in parser.texts]
    return out


def guide_tids(root: Path = GUIDE_DIR) -> set[str]:
    """Every text.js key a setup-guide page asks for (its `tid` attributes)."""
    tids: set[str] = set()
    for page in root.rglob("*.html"):
        tids |= set(re.findall(r'(?<![\w-])tid="([^"]+)"', page.read_text(encoding="utf-8")))
    return tids


def po_language(block: str, po_langs: set[str]) -> str:
    """The .po language of a text.js block: the block name itself (zh_CN, pt_BR, lt) or its language part (fr_FR)."""
    return block if block in po_langs else block.split("_")[0]


def stale_text_js_keys() -> dict[str, list[str]]:
    """Per .po language, the guide keys of its text.js block that still name the upstream product."""
    po_langs = {p.parent.name for p in CATALOG_DIR.glob("*/*.po")}
    tids = guide_tids()
    out: dict[str, list[str]] = {}
    for block, entries in text_js_blocks().items():
        if block == "en":
            continue
        lang = po_language(block, po_langs)
        keys = [k for k, v in entries.items() if k in tids and (has_token(v) or has_native_token(v, lang))]
        if keys:
            out[lang] = keys
    return out
