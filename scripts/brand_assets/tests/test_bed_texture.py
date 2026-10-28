"""Every SVG bed texture a printer profile points at can be drawn by NanoSVG.

The 3D bed is textured by NanoSVG (deps_src/nanosvg/nanosvg.h, loaded in src/slic3r/GUI/GLTexture.cpp). NanoSVG
draws path, rect, circle, ellipse, line, polyline and polygon with inline styles and gradients, and nothing else. It
does not know clipPath, mask, filter, text, image, use, foreignObject, pattern or a <style> sheet: an element it does
not know is skipped but the shapes inside it are still drawn (a clipPath rect becomes an opaque black square), and
a clip-path, mask or filter reference is ignored. A shape styled by a <style> class gets no fill and turns black.

The texture is stretched over the bounding box of the printer's `printable_area` (PartPlate::generate_logo_polygon,
then UVs from the polygon's bounding box in init_model_from_poly), so the viewBox must have the aspect ratio of every
bed that uses it, within ASPECT_TOLERANCE. The printable_area is read from the machine presets whose `printer_model`
is the machine model naming the texture, following `inherits` inside the vendor.

This lives in the brand_assets suite because the Custom printer bed texture is a visible logo of this branch (see
test_visible_logos.py). Scope: every `bed_texture` ending in .svg in the machine profiles of resources/profiles,
found by walking them, so a new profile is checked without editing this file. KNOWN_UNSAFE lists the textures that
fail today and are not ours to change here, with the reason; a test fails when one of them becomes safe, so the
exclusion is removed as soon as it is no longer needed. KNOWN_STRETCHED does the same for printer models whose bed
does not have the aspect ratio of their texture.
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
KNOWN_UNSAFE: dict[str, str] = {}

# A texture may be up to 5% wider or narrower than its bed: the Nova artwork (892.9x623.6) is 4.5% narrower than the
# 300x200 Nova bed, which does not show; a wrong bed is far beyond that (a square texture on a 3:2 bed is 33% off).
ASPECT_TOLERANCE = 0.05

# texture path relative to the repo -> {printer model: why its bed does not have the texture's aspect ratio}
KNOWN_STRETCHED: dict[str, dict[str, str]] = {
    "resources/profiles/cosmyx/Nova-bed_texture.svg": {
        "Cosmyx Nova Double Tete": (
            "the dual-head Nova prints on a 156x200 area (x 68-224) and reuses the 300x200 Nova artwork, so its logo "
            "is squeezed to about half its width; it needs its own texture from Cosmyx (wiki/decision-register.md)"
        ),
    },
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
    if view_box_size(svg) is None:
        problems.append("no viewBox")
    return problems


def view_box_size(svg: bytes) -> tuple[float, float] | None:
    """Width and height of the root viewBox, or None when it is missing or empty."""
    view_box = [float(n) for n in re.split(r"[\s,]+", ET.fromstring(svg).get("viewBox", "").strip()) if n]
    if len(view_box) != 4 or view_box[2] <= 0 or view_box[3] <= 0:
        return None
    return view_box[2], view_box[3]


def bed_sizes(profiles: list[dict]) -> dict[str, dict[str, tuple[float, float]]]:
    """bed_texture -> {printer model: (width, height) of the printable_area bounding box of each of its presets}.

    `profiles` are the machine JSON files of one vendor. A preset inherits the keys it lacks from its `inherits`
    chain; presets of one model that disagree on the bed size are all returned, keyed "model (preset)".
    """
    by_name = {profile.get("name"): profile for profile in profiles}

    def resolved(profile: dict, key: str):
        seen = set()
        while profile is not None and profile.get("name") not in seen:
            if key in profile:
                return profile[key]
            seen.add(profile.get("name"))
            profile = by_name.get(profile.get("inherits"))
        return None

    textures = {p["name"]: p.get("bed_texture", "") for p in profiles if p.get("type") == "machine_model"}
    sizes: dict[str, dict[str, set[tuple[float, float]]]] = {}
    for profile in profiles:
        if profile.get("type") != "machine":
            continue
        model, area = resolved(profile, "printer_model"), resolved(profile, "printable_area")
        if not textures.get(model) or not area:
            continue
        points = [tuple(float(n) for n in point.split("x")) for point in area]
        xs, ys = [x for x, _ in points], [y for _, y in points]
        size = (max(xs) - min(xs), max(ys) - min(ys))
        sizes.setdefault(textures[model], {}).setdefault(model, {})[profile["name"]] = size
    out: dict[str, dict[str, tuple[float, float]]] = {}
    for texture, models in sizes.items():
        for model, presets in models.items():
            if len(set(presets.values())) == 1:
                out.setdefault(texture, {})[model] = next(iter(presets.values()))
            else:
                for preset, size in presets.items():
                    out.setdefault(texture, {})[f"{model} ({preset})"] = size
    return out


def profile_bed_sizes() -> dict[str, dict[str, tuple[float, float]]]:
    """bed_sizes() of every vendor, keyed by the repo-relative POSIX path of each .svg texture."""
    out = {}
    for vendor in sorted(p for p in PROFILES.iterdir() if (p / "machine").is_dir()):
        profiles = [
            json.loads(f.read_text(encoding="utf-8"))
            for f in sorted((vendor / "machine").glob("**/*.json"))
            if not f.name.startswith(".smbdelete")
        ]
        for texture, models in bed_sizes(profiles).items():
            if texture.lower().endswith(".svg"):
                out[(vendor / texture).relative_to(REPO_ROOT).as_posix()] = models
    return out


def stretch(texture: tuple[float, float], bed: tuple[float, float]) -> float:
    """How much wider (> 0) or narrower (< 0) the texture is than the bed it is stretched over, as a fraction."""
    return (texture[0] / texture[1]) / (bed[0] / bed[1]) - 1


def stretched_beds(relative: str) -> dict[str, str]:
    """{printer model: its stretch} for each bed of a texture whose aspect ratio is off by more than the tolerance."""
    size = view_box_size((REPO_ROOT / relative).read_bytes())
    assert size is not None, f"{relative} has no viewBox"
    return {
        model: f"{stretch(size, bed):+.1%} on a {bed[0]:g}x{bed[1]:g} bed"
        for model, bed in profile_bed_sizes().get(relative, {}).items()
        if abs(stretch(size, bed)) > ASPECT_TOLERANCE
    }


def test_custom_printer_bed_texture_is_in_scope():
    assert "resources/profiles/Custom/orcaslicer_bed_texture.svg" in bed_textures()


@pytest.mark.parametrize("relative", [t for t in bed_textures() if t not in KNOWN_UNSAFE])
def test_bed_texture_is_nanosvg_safe(relative):
    assert nanosvg_problems((REPO_ROOT / relative).read_bytes()) == []


def test_every_texture_has_a_bed():
    assert sorted(profile_bed_sizes()) == bed_textures()


@pytest.mark.parametrize("relative", bed_textures())
def test_bed_texture_has_the_aspect_ratio_of_its_beds(relative):
    excluded = KNOWN_STRETCHED.get(relative, {})
    assert {model: off for model, off in stretched_beds(relative).items() if model not in excluded} == {}


def test_known_stretched_beds_still_need_their_exclusion():
    # A loop, not a parametrize: an empty exclusion list must run and pass, not become a pytest skip.
    stale = []
    for relative, models in sorted(KNOWN_STRETCHED.items()):
        for model in models:
            if model not in profile_bed_sizes().get(relative, {}):
                stale.append(f"{model} no longer uses {relative}: drop it from KNOWN_STRETCHED")
            elif model not in stretched_beds(relative):
                stale.append(f"{model} now matches {relative}: drop it from KNOWN_STRETCHED")
    assert stale == []


def test_known_unsafe_textures_still_need_their_exclusion():
    stale = []
    for relative in sorted(KNOWN_UNSAFE):
        if relative not in bed_textures():
            stale.append(f"{relative} is no longer used by a profile: drop it from KNOWN_UNSAFE")
        elif nanosvg_problems((REPO_ROOT / relative).read_bytes()) == []:
            stale.append(f"{relative} is safe now: drop it from KNOWN_UNSAFE")
    assert stale == []


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


@pytest.mark.parametrize("view_box", ["", 'viewBox="0 0 512"', 'viewBox="0 0 512 0"'])
def test_checker_wants_a_view_box(view_box):
    document = f'<svg xmlns="http://www.w3.org/2000/svg" {view_box}/>'.encode()
    assert nanosvg_problems(document) == ["no viewBox"]


def test_checker_accepts_a_rectangular_view_box():
    # The bed is not always square: the aspect ratio is checked against the beds, not here.
    assert nanosvg_problems(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 892.9 623.6"/>') == []


def test_stretch_is_relative_to_the_bed():
    assert stretch((300, 200), (150, 100)) == 0
    assert stretch((512, 512), (300, 200)) == pytest.approx(-1 / 3)
    assert abs(stretch((892.9, 623.6), (300, 200))) < ASPECT_TOLERANCE


def test_bed_sizes_follow_inherits_and_use_the_bounding_box():
    profiles = [
        {"type": "machine_model", "name": "M", "bed_texture": "m.svg"},
        {"type": "machine_model", "name": "Png", "bed_texture": "p.png"},
        {"type": "machine", "name": "common", "printable_area": ["10x0", "310x0", "310x200", "10x200"]},
        {"type": "machine", "name": "M 0.4", "inherits": "common", "printer_model": "M"},
        {"type": "machine", "name": "M 0.6", "inherits": "M 0.4"},
        {"type": "machine", "name": "orphan", "printer_model": "unknown", "printable_area": ["0x0", "1x1"]},
    ]
    assert bed_sizes(profiles) == {"m.svg": {"M": (300.0, 200.0)}}


def test_bed_sizes_list_presets_of_one_model_that_disagree():
    profiles = [
        {"type": "machine_model", "name": "M", "bed_texture": "m.svg"},
        {"type": "machine", "name": "a", "printer_model": "M", "printable_area": ["0x0", "300x200"]},
        {"type": "machine", "name": "b", "printer_model": "M", "printable_area": ["0x0", "200x200"]},
    ]
    assert bed_sizes(profiles) == {"m.svg": {"M (a)": (300.0, 200.0), "M (b)": (200.0, 200.0)}}
