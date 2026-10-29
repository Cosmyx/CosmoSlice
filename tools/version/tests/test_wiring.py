"""The app shows the built version and the CI names builds with it.

The C++ is built by GitHub CI only (D-007), so this checks the text of the files that carry the version.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def read_path(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_version_inc_builds_the_version_from_its_parts() -> None:
    assert 'set(COSMOSLICE_VERSION "${SoftFever_VERSION}-${COSMYX_PATCH_VERSION}")' in read("version.inc")


def test_the_version_header_exposes_the_built_version() -> None:
    assert '#define COSMOSLICE_VERSION "@COSMOSLICE_VERSION@"' in read("src/libslic3r/libslic3r_version.h.in")


def test_about_dialog_and_splash_show_the_built_version() -> None:
    about = read("src/slic3r/GUI/AboutDialog.cpp")
    assert "auto          version_string = GUI_App::format_display_version();" in about
    assert "Cosmyx Bundle Version" not in about
    assert re.search(r"version_display = COSMOSLICE_VERSION;", read("src/slic3r/GUI/GUI_App.cpp"))


def test_network_test_dialog_shows_the_built_version() -> None:
    dialog = read("src/slic3r/GUI/NetworkTestDialog.cpp")
    assert "return wxString(GUI_App::format_display_version());" in dialog
    assert "SoftFever_VERSION" not in dialog


def test_the_gui_no_longer_shows_the_bare_patch_number() -> None:
    gui = REPO_ROOT / "src" / "slic3r"
    found = [str(p.relative_to(REPO_ROOT)) for p in gui.rglob("*.cpp") if "COSMYX_PATCH_VERSION" in read_path(p)]
    assert not found, found


def test_ci_names_builds_with_the_build_tag() -> None:
    naming = read(".github/workflows/cosmyx-artifact-naming.yml")
    assert "tools/version/cosmoslice_version.py build-tag" in naming
    build = read(".github/workflows/build_orca.yml")
    names = re.findall(r"^ +name: (CosmoSlice_.+)$", build, re.MULTILINE)
    assert len(names) == 4, names
    assert all("${{ env.cosmyx_build_tag }}" in name for name in names), names
    assert "cosmyx_patch_ver" not in build
