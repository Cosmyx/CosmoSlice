"""No Orca logo is left where users see it, and every macOS icon file is a valid ICNS.

ORCA_DENYLIST holds the SHA-256 and size of the Orca files this branch replaced. It was computed once, by hand,
from the git blobs (no git at test time):

    git show <rev>:<path> | shasum -a 256        # and `| wc -c` for the size

with <rev> = a6f1ed8ab4 (last Orca version) for every path, except resources/images/OrcaSlicer.icns, whose last
Orca version is b56bbbff4e (d317226e47 replaced it by a corrupt file). Files still waiting for a CosmoSlice
asset (bed texture, logo2.png) are not listed, otherwise the suite would be red on pending assets.
"""

import hashlib
from pathlib import Path

import icns
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RESOURCES = REPO_ROOT / "resources"

# (sha256, size in bytes) -> what the Orca file was
ORCA_DENYLIST: dict[tuple[str, int], str] = {
    ("e50995e3e3c48d57bef4ee724035e430d4919ca8d8ef32e7df556ac6fc78db19", 756272): "Orca resources/Icon.icns",
    ("33850360e20b58c180a6545d4f5822a090178d3581e291646f41f3a516158dc6", 401478): "Orca images/OrcaSlicer.icns",
    ("5f7172b793925880162cf08c4c2779b251fc126329e7bcf01afbf8d3f2a0b3d9", 9658): "Orca web/image/logo.png",
    ("f3b752c2c164b3d0f58a5af9c96684b16ce4c95f0417c9b8ae88412c5d185ef2", 387692): "Orca images/stl.icns",
    ("6dbb6884d436d79342d426f59747a260e13beebeea46f22149df37936e59031e", 403221): "Orca images/gcode.icns",
}
DENYLIST_SIZES = {size for _, size in ORCA_DENYLIST}

# path -> where users see it
VISIBLE_LOGOS: dict[str, str] = {
    "resources/web/image/logo.png": "home page and setup guide header (homepage/index.html, guide/1/index.html)",
    "resources/Icon.icns": "macOS app bundle icon: Finder, Dock, About (CFBundleIconFile)",
    "resources/images/OrcaSlicer.icns": "macOS document icon of .obj, .amf and .3mf files",
    "resources/images/stl.icns": "macOS document icon of .stl files (app icon until A2 lands, D-011)",
    "resources/images/gcode.icns": "macOS document icon of .gcode files (app icon until A2 lands, D-011)",
}


def fingerprint(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def resource_files() -> list[Path]:
    return sorted(p for p in RESOURCES.rglob("*") if p.is_file() and not p.name.startswith(".smbdelete"))


@pytest.mark.parametrize("relative", sorted(VISIBLE_LOGOS))
def test_visible_logo_is_not_orca(relative):
    path = REPO_ROOT / relative
    assert path.is_file(), relative
    found = ORCA_DENYLIST.get(fingerprint(path))
    assert found is None, f"{relative} ({VISIBLE_LOGOS[relative]}) is still the {found}"


def test_no_orca_logo_anywhere_in_resources():
    offenders = []
    for path in resource_files():
        if path.stat().st_size not in DENYLIST_SIZES:
            continue
        found = ORCA_DENYLIST.get(fingerprint(path))
        if found is not None:
            offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {found}")
    assert offenders == []


def test_every_icns_in_resources_is_valid():
    broken = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in resource_files()
        if p.suffix == ".icns" and not icns.is_valid_icns(p.read_bytes())
    ]
    assert broken == []
