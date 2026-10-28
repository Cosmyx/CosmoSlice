"""Manifest of derived assets: the committed file, and the loader's validation rules."""

from pathlib import Path, PurePosixPath

import pytest
from brand_assets import derive

REPO_ROOT = Path(__file__).resolve().parents[3]


def committed_entries() -> list[derive.Entry]:
    return derive.load_manifest(derive.MANIFEST, REPO_ROOT)


def test_committed_manifest_parses():
    committed_entries()


def test_committed_sources_exist_and_are_svg():
    for entry in committed_entries():
        path = REPO_ROOT / entry.source
        assert path.is_file(), entry.source
        assert path.suffix == ".svg", entry.source
        assert b"<svg" in path.read_bytes(), entry.source


def test_committed_outputs_exist_under_resources():
    for entry in committed_entries():
        assert PurePosixPath(entry.output).parts[0] == "resources", entry.output
        assert (REPO_ROOT / entry.output).is_file(), entry.output


def write_manifest(tmp_path: Path, body: str) -> Path:
    (tmp_path / "src.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "out.png").write_bytes(b"")
    manifest = tmp_path / "derived-assets.toml"
    manifest.write_text(body, encoding="utf-8")
    return manifest


def test_loader_reads_entries(tmp_path):
    manifest = write_manifest(
        tmp_path,
        '[[derived]]\nsource = "src.svg"\noutput = "out.png"\nformat = "png"\nsize = 154\n'
        '[[derived]]\nsource = "src.svg"\noutput = "out.icns"\nformat = "icns"\n',
    )
    assert derive.load_manifest(manifest, tmp_path) == [
        derive.Entry("src.svg", "out.png", "png", 154),
        derive.Entry("src.svg", "out.icns", "icns", None),
    ]


def test_loader_accepts_an_empty_manifest(tmp_path):
    assert derive.load_manifest(write_manifest(tmp_path, "# nothing yet\n"), tmp_path) == []


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ('source = "src.svg"\noutput = "out.png"\nformat = "png"\n', "size"),
        ('source = "src.svg"\noutput = "out.png"\nformat = "png"\nsize = 0\n', "size"),
        ('source = "src.svg"\noutput = "out.icns"\nformat = "icns"\nsize = 16\n', "size"),
        ('source = "src.svg"\noutput = "out.gif"\nformat = "gif"\n', "format"),
        ('source = "/abs/src.svg"\noutput = "out.png"\nformat = "png"\nsize = 8\n', "relative"),
        ('source = "src.svg"\noutput = "a\\\\out.png"\nformat = "png"\nsize = 8\n', "POSIX"),
        ('source = "../src.svg"\noutput = "out.png"\nformat = "png"\nsize = 8\n', "relative"),
        ('source = "src.svg"\noutput = "src.svg"\nformat = "png"\nsize = 8\n', "source"),
        ('source = "src.svg"\noutput = "out.png"\nformat = "png"\nsize = 8\nextra = 1\n', "unknown"),
        ('source = "missing.svg"\noutput = "out.png"\nformat = "png"\nsize = 8\n', "does not exist"),
    ],
    ids=[
        "png-without-size",
        "png-zero-size",
        "icns-with-size",
        "bad-format",
        "absolute",
        "backslash",
        "parent",
        "output-is-source",
        "unknown-key",
        "missing-source",
    ],
)
def test_loader_rejects_invalid_entries(tmp_path, body, message):
    manifest = write_manifest(tmp_path, "[[derived]]\n" + body)
    with pytest.raises(ValueError, match=message):
        derive.load_manifest(manifest, tmp_path)


def test_loader_rejects_duplicate_outputs(tmp_path):
    entry = '[[derived]]\nsource = "src.svg"\noutput = "out.png"\nformat = "png"\nsize = 8\n'
    with pytest.raises(ValueError, match="duplicate"):
        derive.load_manifest(write_manifest(tmp_path, entry * 2), tmp_path)


def test_loader_rejects_an_entry_that_is_not_a_table(tmp_path):
    manifest = write_manifest(tmp_path, 'derived = ["src.svg"]\n')
    with pytest.raises(ValueError, match="entry 1: must be a table"):
        derive.load_manifest(manifest, tmp_path)


@pytest.mark.parametrize(
    "body",
    ['derived = "src.svg"\n', "derived = 3\n", '[derived]\nsource = "src.svg"\n'],
    ids=["string", "integer", "single-table"],
)
def test_loader_rejects_a_derived_key_that_is_not_an_array(tmp_path, body):
    with pytest.raises(ValueError, match=r"derived must be an array of tables \(\[\[derived\]\]\)"):
        derive.load_manifest(write_manifest(tmp_path, body), tmp_path)
