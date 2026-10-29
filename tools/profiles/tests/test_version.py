"""The Cosmyx vendor version derived from the commit date, checked against a model of the slicer's own rules.

The slicer is C++ and its tests are not built in CI, so the parse and reinstall rules are modelled here in Python,
line by line from the source they cite. This is a model, not the real code (D-013): when the cited lines change,
the model has to follow.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import cosmyx_index
import pytest

INT_MAX = 2147483647  # semver_t fields are int (deps_src/semver/semver.h)
SLICE_SIZE = 50  # deps_src/semver/semver.c:13
MAX_SIZE = 255  # has_valid_length, deps_src/semver/semver.c:551
VALID_CHARS = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-+")  # semver.c:17-20
LEGACY_VERSION = "01.07.00.19"  # the hand-written version of resources/profiles/cosmyx.json at 3cc7dc1df7


def semver_parse(text: str) -> tuple[int, int, int] | None:
    """Model of semver_parse (semver.c:142) and semver_parse_version (semver.c:175) for plain dotted versions.

    Returns (major, minor, patch), or None where the C code returns -1. A fourth part is folded into the patch as
    patch * 100 + part (semver.c:202). Prerelease and metadata suffixes are out of the model (rejected).
    """
    if len(text) > MAX_SIZE or any(c not in VALID_CHARS for c in text):
        return None
    if "-" in text or "+" in text:
        return None
    parts = text.split(".")
    if len(parts) not in (2, 3, 4):
        return None
    values = []
    for part in parts:
        if len(part) > SLICE_SIZE:
            return None
        # strtol on an empty slice stops at once, which the C code accepts as 0.
        if part and not part.isdigit():
            return None
        value = int(part) if part else 0
        if value > INT_MAX:
            return None
        values.append(value)
    major, minor = values[0], values[1]
    patch = values[2] if len(values) > 2 else 0
    if len(values) == 4:
        patch = patch * 100 + values[3]
        if patch > INT_MAX:
            return None
    return major, minor, patch


def semver_to_string(version: tuple[int, int, int]) -> str:
    """Model of Semver::to_string (src/libslic3r/Semver.hpp:157): maj.min.(patch/100).(patch%100)."""
    major, minor, patch = version
    return f"{major}.{minor}.{patch // 100}.{patch % 100}"


def reinstalls(bundled: str, installed: str) -> bool:
    """Model of PresetUpdater::priv::check_installed_vendor_profiles (src/slic3r/Utils/PresetUpdater.cpp:1123-1125).

    The bundled vendor index replaces the installed copy when major or minor differ, or when the installed one is
    lower (semver_compare_version, semver.c:292: major, then minor, then patch).
    """
    resource_ver = semver_parse(bundled)
    vendor_ver = semver_parse(installed)
    assert resource_ver is not None
    assert vendor_ver is not None
    version_match = resource_ver[:2] == vendor_ver[:2]
    return not version_match or vendor_ver < resource_ver


def version(date: datetime) -> str:
    return cosmyx_index.version_from_commit_date(date.isoformat())


@pytest.mark.parametrize(
    ("commit_date", "expected"),
    [
        ("2026-10-29T14:03:12+01:00", "20261029.130312.00.00"),
        ("2026-10-29T13:03:12Z", "20261029.130312.00.00"),
        ("2026-10-29T13:03:12+00:00", "20261029.130312.00.00"),
        ("2026-01-01T00:00:00+00:00", "20260101.000000.00.00"),
        ("2026-01-01T00:30:00+01:00", "20251231.233000.00.00"),
        ("2026-02-03T04:05:06-02:00", "20260203.060506.00.00"),
    ],
)
def test_version_is_the_utc_commit_date(commit_date: str, expected: str) -> None:
    assert cosmyx_index.version_from_commit_date(commit_date) == expected


def test_leading_zeros_parse_as_decimal() -> None:
    assert semver_parse("20260203.040506.00.00") == (20260203, 40506, 0)
    assert semver_parse("20260101.000000.00.00") == (20260101, 0, 0)


@pytest.mark.parametrize("commit_date", ["2026-10-29T14:03:12", "2026-10-29", "not a date", ""])
def test_a_date_without_utc_offset_is_rejected(commit_date: str) -> None:
    with pytest.raises(cosmyx_index.CosmyxIndexError):
        cosmyx_index.version_from_commit_date(commit_date)


def test_sub_second_dates_are_rejected() -> None:
    with pytest.raises(cosmyx_index.CosmyxIndexError, match="whole second"):
        cosmyx_index.version_from_commit_date("2026-10-29T14:03:12.5+00:00")


def sample_dates() -> list[datetime]:
    """A fixed sweep of instants around boundaries (second, minute, hour, day, month, year, leap day)."""
    utc = timezone(timedelta(0))
    anchors = [
        datetime(2026, 10, 29, 13, 3, 12, tzinfo=utc),
        datetime(2026, 12, 31, 23, 59, 59, tzinfo=utc),
        datetime(2028, 2, 28, 23, 59, 59, tzinfo=utc),
        datetime(2000, 1, 1, 0, 0, 0, tzinfo=utc),
    ]
    steps = [timedelta(seconds=s) for s in (0, 1, 59, 60, 61, 3599, 3600, 86399, 86400, 86401, 31 * 86400)]
    return sorted({anchor + step for anchor in anchors for step in steps})


def test_a_later_commit_has_a_greater_version() -> None:
    dates = sample_dates()
    parsed = [semver_parse(version(d)) for d in dates]
    assert all(p is not None for p in parsed)
    assert parsed == sorted(parsed)
    assert len(set(parsed)) == len(parsed)


def test_different_commits_differ_in_major_or_minor() -> None:
    dates = sample_dates()
    keys = [semver_parse(version(d))[:2] for d in dates]
    assert len(set(keys)) == len(keys)


def test_offsets_of_one_instant_give_one_version() -> None:
    instant = datetime(2026, 10, 29, 13, 3, 12, tzinfo=timezone(timedelta(0)))
    versions = {version(instant.astimezone(timezone(timedelta(hours=h)))) for h in (-11, -2, 0, 1, 5, 13)}
    assert versions == {"20261029.130312.00.00"}


@pytest.mark.parametrize(
    "date",
    [
        datetime(1, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(0))),
        datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone(timedelta(0))),
    ],
)
def test_bounds_fit_the_semver_parser(date: datetime) -> None:
    text = version(date)
    assert len(text) <= MAX_SIZE
    assert all(len(part) <= SLICE_SIZE for part in text.split("."))
    parsed = semver_parse(text)
    assert parsed is not None
    assert all(0 <= value <= INT_MAX for value in parsed)


def test_version_round_trips_through_to_string() -> None:
    for date in sample_dates():
        parsed = semver_parse(version(date))
        assert semver_parse(semver_to_string(parsed)) == parsed


def test_the_model_rejects_what_the_parser_rejects() -> None:
    assert semver_parse("1") is None
    assert semver_parse("1.2.3.4.5") is None
    assert semver_parse("2147483648.0") is None
    assert semver_parse("1.2.3.04") == (1, 2, 304)
    assert semver_parse(LEGACY_VERSION) == (1, 7, 19)


def test_a_newer_build_reinstalls() -> None:
    old = version(datetime(2026, 10, 29, 13, 3, 12, tzinfo=timezone(timedelta(0))))
    new = version(datetime(2026, 10, 29, 13, 3, 13, tzinfo=timezone(timedelta(0))))
    assert reinstalls(bundled=new, installed=old)


def test_an_older_build_reinstalls() -> None:
    old = version(datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone(timedelta(0))))
    new = version(datetime(2026, 10, 29, 0, 0, 0, tzinfo=timezone(timedelta(0))))
    assert reinstalls(bundled=old, installed=new)


def test_the_legacy_hand_written_version_is_replaced() -> None:
    new = version(datetime(2026, 10, 29, 13, 3, 12, tzinfo=timezone(timedelta(0))))
    assert reinstalls(bundled=new, installed=LEGACY_VERSION)


def test_the_same_commit_does_not_reinstall() -> None:
    same = version(datetime(2026, 10, 29, 13, 3, 12, tzinfo=timezone(timedelta(0))))
    assert not reinstalls(bundled=same, installed=same)
