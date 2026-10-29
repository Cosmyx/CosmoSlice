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


WORKFLOWS = REPO_ROOT / ".github" / "workflows"
STEP_START = re.compile(r"^ *- (name|uses): *(.+?) *$")
GENERATE = "Generate Cosmyx vendor index"
GENERATE_COMMAND = "tools/profiles/cosmyx_index.py generate --out resources/profiles/cosmyx.json"
BRANCH_ENV = "COSMYX_BRANCH: ${{ github.head_ref || github.ref_name }}"
# Packaged copy checked after each OS build: (check step, build step it follows, upload step it precedes, path).
PACKAGED = [
    (
        "Check packaged Cosmyx index mac",
        "Build slicer mac",
        "Upload artifacts mac",
        "build/universal/OrcaSlicer/OrcaSlicer.app/Contents/Resources/profiles/cosmyx.json",
    ),
    (
        "Check packaged Cosmyx index Win",
        "Build slicer Win",
        "Upload artifacts Win zip",
        "build/OrcaSlicer/resources/profiles/cosmyx.json",
    ),
    (
        "Check packaged Cosmyx index Linux",
        "Build slicer",
        "Upload artifacts Ubuntu",
        "build/package/resources/profiles/cosmyx.json",
    ),
]


def steps(workflow: str) -> list[tuple[str, str]]:
    """(label, text) of every step of a workflow, in file order; the label is the step's name or its action."""
    lines = (WORKFLOWS / workflow).read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if STEP_START.match(line)]
    return [
        (STEP_START.match(lines[start])[2], "\n".join(lines[start:end]))
        for start, end in zip(starts, [*starts[1:], len(lines)], strict=False)
    ]


def index_of(found: list[tuple[str, str]], label: str) -> int:
    labels = [name for name, _ in found]
    assert labels.count(label) == 1, f"step '{label}' found {labels.count(label)} times"
    return labels.index(label)


def assert_generates_right_after_checkout(workflow: str, checkout: str) -> None:
    found = steps(workflow)
    at = index_of(found, GENERATE)
    assert at == index_of(found, checkout) + 1, workflow
    block = found[at][1]
    assert GENERATE_COMMAND in block
    assert '--branch "$COSMYX_BRANCH"' in block
    assert BRANCH_ENV in block
    assert "shell: bash" in block


def test_build_generates_the_index_after_checkout() -> None:
    assert_generates_right_after_checkout("build_orca.yml", "Checkout")


def test_profile_check_generates_the_index_before_validating() -> None:
    assert_generates_right_after_checkout("check_profiles.yml", "Checkout repository")
    found = steps("check_profiles.yml")
    assert index_of(found, GENERATE) < index_of(found, "Run extra JSON check")


def test_flatpak_generates_the_index_after_checkout() -> None:
    assert_generates_right_after_checkout("build_all.yml", "actions/checkout@v5")


def test_each_build_verifies_its_packaged_index() -> None:
    found = steps("build_orca.yml")
    for check, build, upload, path in PACKAGED:
        at = index_of(found, check)
        assert index_of(found, build) < at < index_of(found, upload), check
        block = found[at][1]
        assert f"tools/profiles/cosmyx_index.py verify --index {path}" in block, check
        assert '--branch "$COSMYX_BRANCH"' in block, check
        assert BRANCH_ENV in block, check


def test_the_generated_index_is_ignored_by_git() -> None:
    rel = cosmyx_index.DEFAULT_OUT.relative_to(REPO_ROOT).as_posix()
    lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert f"/{rel}" in lines
