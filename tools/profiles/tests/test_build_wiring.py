"""The C++ build refuses to configure without the generated Cosmyx index.

CMake is not run in the CI image (the slicer is built by GitHub CI only, D-007), so this checks the guard's text:
it must test the very file the generator writes, stop the configure step, and point to the recipe.
"""

from __future__ import annotations

import re
from pathlib import Path

import cosmyx_index

REPO_ROOT = Path(__file__).resolve().parents[3]
CMAKE = REPO_ROOT / "CMakeLists.txt"
GUARD = re.compile(
    r'if\s*\(\s*NOT\s+EXISTS\s+"\$\{SLIC3R_RESOURCES_DIR\}/(?P<path>[^"]+)"\s*\)\s*'
    r"message\s*\(\s*FATAL_ERROR\s+(?P<message>.*?)\)\s*endif\s*\(\s*\)",
    re.DOTALL,
)


def test_cmake_stops_when_the_cosmyx_index_is_missing() -> None:
    text = CMAKE.read_text(encoding="utf-8")
    match = GUARD.search(text)
    assert match, "no FATAL_ERROR guard on a resources file in CMakeLists.txt"
    resources = REPO_ROOT / "resources"
    assert match["path"] == cosmyx_index.DEFAULT_OUT.relative_to(resources).as_posix()
    assert "just profiles-index" in match["message"]
    assert text.index("set(SLIC3R_RESOURCES_DIR") < match.start() < text.index("add_subdirectory(src)")
