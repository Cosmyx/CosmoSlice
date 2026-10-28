"""Every committed derived asset is byte-identical to a fresh render of its source.

Needs the pinned resvg: run it with `just test brand_assets` (CI image). Outside the image it fails with a hint,
it never skips.
"""

from pathlib import Path

import pytest
from brand_assets import derive

REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRIES = derive.load_manifest(derive.MANIFEST, REPO_ROOT)


def test_manifest_is_not_empty():
    assert ENTRIES, "derived-assets.toml lists no output"


@pytest.mark.parametrize("entry", ENTRIES, ids=[entry.output for entry in ENTRIES])
def test_committed_output_matches_fresh_render(entry):
    render = derive.resvg_renderer()
    fresh = derive.render_entry(entry, REPO_ROOT, render)
    committed = (REPO_ROOT / entry.output).read_bytes()
    assert committed == fresh, f"{entry.output} is stale: run `just -f scripts/brand_assets/justfile derive`"
