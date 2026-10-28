"""Every SVG bed texture a printer profile points at can be drawn by NanoSVG.

The 3D bed is textured by NanoSVG (deps_src/nanosvg/nanosvg.h, loaded in src/slic3r/GUI/GLTexture.cpp). NanoSVG
draws path, rect, circle, ellipse, line, polyline and polygon with inline styles and gradients, and nothing else. It
does not know clipPath, mask, filter, text, image, use, foreignObject, pattern or a <style> sheet: an element it does
not know is skipped but the shapes inside it are still drawn (a clipPath rect becomes an opaque black square), and
a clip-path, mask or filter reference is ignored. A shape styled by a <style> class gets no fill and turns black.
The bed texture is stretched over a square bed by default, so its viewBox has to be square.

This lives in the brand_assets suite because the Custom printer bed texture is a visible logo of this branch (see
test_visible_logos.py). Scope: every `bed_texture` ending in .svg in the machine profiles of resources/profiles,
found by walking them, so a new profile is checked without editing this file. KNOWN_UNSAFE lists the textures that
fail today and are not ours to change here, with the reason; a test fails when one of them becomes safe, so the
exclusion is removed as soon as it is no longer needed.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILES = REPO_ROOT / "resources" / "profiles"
SVG_NS = "{http://www.w3.org/2000/svg}"

UNSUPPORTED_ELEMENTS = frozenset(
    {"clipPath", "mask", "filter", "text", "image", "use", "foreignObject", "pattern", "style"}
)
UNSUPPORTED_PROPERTIES = frozenset({"clip-path", "mask", "filter"})

# texture path relative to the repo -> why it is not checked
KNOWN_UNSAFE: dict[str, str] = {
    "resources/profiles/cosmyx/Nova-bed_texture.svg": (
        "Nova bed artwork from the cosmyx profile pack (spyder-2.3.1-4, bbdb867909), not produced by this branch: "
        "its fills come from a <style> sheet NanoSVG ignores, and its viewBox follows the rectangular Nova bed"
    ),
}


def bed_textures() -> list[str]:
    """Repo-relative POSIX paths of every .svg named by a machine profile's `bed_texture`."""
    found = set()
    for profile in PROFILES.glob("*/machine/**/*.json"):
        if profile.name.startswith(".smbdelete"):
            continue
        texture = json.loads(profile.read_text(encoding="utf-8")).get("bed_texture", "")
        if texture.endswith(".svg"):
            vendor = profile.relative_to(PROFILES).parts[0]
            found.add((PROFILES / vendor / texture).relative_to(REPO_ROOT).as_posix())
    return sorted(found)


def nanosvg_problems(svg: bytes) -> list[str]:
    """What NanoSVG would draw differently from a browser, or an empty list."""
    root = ET.fromstring(svg)
    problems = []
    if root.tag != SVG_NS + "svg":
        problems.append(f"root element is {root.tag}, not an SVG <svg>")
    for element in root.iter():
        tag = element.tag
        if isinstance(tag, str) and tag.startswith(SVG_NS) and tag[len(SVG_NS) :] in UNSUPPORTED_ELEMENTS:
            problems.append(f"<{tag[len(SVG_NS) :]}> element")
        for name, value in element.attrib.items():
            if name in UNSUPPORTED_PROPERTIES:
                problems.append(f"{name} attribute")
            if name == "style":
                for declaration in value.split(";"):
                    prop = declaration.split(":", 1)[0].strip()
                    if prop in UNSUPPORTED_PROPERTIES:
                        problems.append(f"{prop} in a style attribute")
    view_box = [float(n) for n in re.split(r"[\s,]+", root.get("viewBox", "").strip()) if n]
    if len(view_box) != 4:
        problems.append("no viewBox")
    elif view_box[2] != view_box[3]:
        problems.append(f"viewBox {view_box[2]:g}x{view_box[3]:g} is not square")
    return problems


def test_custom_printer_bed_texture_is_in_scope():
    assert "resources/profiles/Custom/orcaslicer_bed_texture.svg" in bed_textures()


@pytest.mark.parametrize("relative", [t for t in bed_textures() if t not in KNOWN_UNSAFE])
def test_bed_texture_is_nanosvg_safe(relative):
    assert nanosvg_problems((REPO_ROOT / relative).read_bytes()) == []


@pytest.mark.parametrize("relative", sorted(KNOWN_UNSAFE))
def test_known_unsafe_texture_still_needs_its_exclusion(relative):
    assert relative in bed_textures(), f"{relative} is no longer used by a profile: drop it from KNOWN_UNSAFE"
    assert nanosvg_problems((REPO_ROOT / relative).read_bytes()) != [], f"{relative} is safe now: drop it"


SAFE = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    b'<g style="fill-rule:evenodd;clip-rule:evenodd"><rect width="10" height="10"/></g></svg>'
)


def test_checker_accepts_plain_shapes():
    # clip-rule is a fill rule NanoSVG reads, not a clip: it must not be taken for clip-path.
    assert nanosvg_problems(SAFE) == []


@pytest.mark.parametrize(
    ("svg", "problem"),
    [
        (b'<clipPath id="c"><rect width="1" height="1"/></clipPath>', "<clipPath> element"),
        (b"<mask/>", "<mask> element"),
        (b"<filter/>", "<filter> element"),
        (b"<text>x</text>", "<text> element"),
        (b"<image/>", "<image> element"),
        (b"<use/>", "<use> element"),
        (b"<foreignObject/>", "<foreignObject> element"),
        (b"<pattern/>", "<pattern> element"),
        (b"<style>.a{fill:red}</style>", "<style> element"),
        (b'<g clip-path="url(#c)"/>', "clip-path attribute"),
        (b'<g mask="url(#m)"/>', "mask attribute"),
        (b'<g filter="url(#f)"/>', "filter attribute"),
        (b'<g style="fill:red; clip-path:url(#c)"/>', "clip-path in a style attribute"),
    ],
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_checker_rejects_what_nanosvg_cannot_draw(svg, problem):
    document = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">' + svg + b"</svg>"
    assert nanosvg_problems(document) == [problem]


def test_checker_ignores_foreign_namespaces():
    document = (
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:x="urn:editor" viewBox="0 0 512 512">'
        b'<x:text/><g x:filter="1"/></svg>'
    )
    assert nanosvg_problems(document) == []


@pytest.mark.parametrize(
    ("view_box", "problem"),
    [
        ('viewBox="0 0 892.9 623.6"', "viewBox 892.9x623.6 is not square"),
        ("", "no viewBox"),
    ],
)
def test_checker_wants_a_square_view_box(view_box, problem):
    document = f'<svg xmlns="http://www.w3.org/2000/svg" {view_box}/>'.encode()
    assert nanosvg_problems(document) == [problem]
