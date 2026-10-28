"""Minimal, byte-preserving reader and writer for gettext .po/.pot catalogues.

The parser keeps every entry's original lines, so a tool can rewrite one field of one entry and leave every other
byte of the file untouched. Rendering follows GNU gettext's layout (79-column wrapping, break after spaces and after
an escaped newline), so rewritten fields look like the ones msgmerge writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PAGE_WIDTH = 79

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "a": "\a", "b": "\b", "f": "\f", "v": "\v"}
_QUOTES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t", "\r": "\\r"}
_KEYWORD = re.compile(r'^(?P<obsolete>#~ )?(?P<kw>msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(?P<str>".*")\s*$')
_CONTINUATION = re.compile(r'^(?P<obsolete>#~ )?(?P<str>".*")\s*$')


def unquote(literal: str) -> str:
    """Decode one quoted PO string literal (with its quotes)."""
    if len(literal) < 2 or literal[0] != '"' or literal[-1] != '"':
        raise ValueError(f"not a PO string literal: {literal!r}")
    body = literal[1:-1]
    out: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
                i += 2
                continue
            if nxt in "01234567":
                digits = re.match(r"[0-7]{1,3}", body[i + 1 :]).group(0)
                out.append(chr(int(digits, 8)))
                i += 1 + len(digits)
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def quote(text: str) -> str:
    """Escape a string for a PO literal (without the surrounding quotes)."""
    return "".join(_QUOTES.get(ch, ch) for ch in text)


def _wrap_segment(escaped: str, width: int) -> list[str]:
    """Split an escaped segment into chunks of at most `width` characters, breaking after spaces."""
    chunks: list[str] = []
    rest = escaped
    while len(rest) > width:
        cut = rest.rfind(" ", 0, width)
        if cut < 0:
            cut = rest.find(" ", width)
            if cut < 0:
                break
        chunks.append(rest[: cut + 1])
        rest = rest[cut + 1 :]
    if rest or not chunks:
        chunks.append(rest)
    return chunks


def render_field(keyword: str, value: str, prefix: str = "") -> list[str]:
    """Render `keyword "value"` the way GNU gettext lays it out, each line starting with `prefix` (e.g. "#| ")."""
    escaped = quote(value)
    single = f'{prefix}{keyword} "{escaped}"'
    newline_inside = "\\n" in escaped[:-2] if escaped.endswith("\\n") else "\\n" in escaped
    if len(single) <= PAGE_WIDTH and not newline_inside:
        return [single]
    segments = [s for s in re.split(r"(?<=\\n)", escaped) if s]
    width = PAGE_WIDTH - len(prefix) - 2
    lines = [f'{prefix}{keyword} ""']
    for segment in segments:
        lines += [f'{prefix}"{chunk}"' for chunk in _wrap_segment(segment, width)]
    return lines


@dataclass
class Field:
    """One keyword of an entry and the [start, end) line span it occupies in the file."""

    keyword: str
    value: str
    start: int
    end: int


@dataclass
class Entry:
    """One catalogue entry: its comment lines and fields, with line spans into the file's line list."""

    start: int
    end: int
    obsolete: bool = False
    comments: list[tuple[int, str]] = field(default_factory=list)
    fields: list[Field] = field(default_factory=list)

    def get(self, keyword: str) -> Field | None:
        return next((f for f in self.fields if f.keyword == keyword), None)

    @property
    def msgid(self) -> str:
        f = self.get("msgid")
        return f.value if f else ""

    @property
    def msgctxt(self) -> str | None:
        f = self.get("msgctxt")
        return f.value if f else None

    @property
    def msgstrs(self) -> list[str]:
        return [f.value for f in self.fields if f.keyword.startswith("msgstr")]

    @property
    def is_header(self) -> bool:
        return self.msgid == "" and self.msgctxt is None and not self.obsolete

    @property
    def flags(self) -> list[str]:
        out: list[str] = []
        for _, line in self.comments:
            if line.startswith("#,"):
                out += [f.strip() for f in line[2:].split(",") if f.strip()]
        return out

    @property
    def is_fuzzy(self) -> bool:
        return "fuzzy" in self.flags

    @property
    def translated(self) -> bool:
        return any(self.msgstrs)


def split_lines(text: str) -> list[str]:
    """Split file text into lines without their LF (the file must not contain CR)."""
    if "\r" in text:
        raise ValueError("catalogue contains CR characters; every catalogue must be LF")
    return text.split("\n")


def parse(text: str) -> tuple[list[str], list[Entry]]:
    """Parse a catalogue into its lines and its entries (blank-line separated blocks)."""
    lines = split_lines(text)
    entries: list[Entry] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].strip():
            i += 1
        entry = _parse_block(lines, start, i)
        if entry.fields:
            entries.append(entry)
    return lines, entries


def _parse_block(lines: list[str], start: int, end: int) -> Entry:
    entry = Entry(start=start, end=end)
    current: Field | None = None
    parts: list[str] = []

    def close(at: int) -> None:
        nonlocal current, parts
        if current is not None:
            current.value = "".join(unquote(p) for p in parts)
            current.end = at
            entry.fields.append(current)
        current, parts = None, []

    for n in range(start, end):
        line = lines[n]
        keyword = _KEYWORD.match(line)
        if keyword:
            close(n)
            entry.obsolete = entry.obsolete or bool(keyword.group("obsolete"))
            current = Field(keyword.group("kw"), "", n, n + 1)
            parts = [keyword.group("str")]
            continue
        continuation = _CONTINUATION.match(line)
        if continuation and current is not None:
            parts.append(continuation.group("str"))
            continue
        close(n)
        if line.startswith("#"):
            entry.comments.append((n, line))
            continue
        raise ValueError(f"line {n + 1}: unexpected content in catalogue: {line!r}")
    close(end)
    return entry


def active_entries(entries: list[Entry]) -> list[Entry]:
    """Entries that are neither the header nor obsolete (#~)."""
    return [e for e in entries if not e.is_header and not e.obsolete]
