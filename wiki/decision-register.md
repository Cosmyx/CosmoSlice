# Decision register

Every decision taken while working on CosmoSlice is recorded here with its number, so later changes can find why the
code is the way it is. Numbers are never reused. An entry gives the context, the decision, the reason, and what
reverting it would take. Problems found but not fixed go to [Open issues](#open-issues).

## D-007 Tooling: root justfile, pinned CI image, Python tests and lint in Docker

- **Context.** The repository had no task runner and no Python test or lint setup; scripts were run by hand.
- **Decision.** A root `justfile` holds every manual operation. Python tests (pytest) and lint (ruff) run in one
  pinned CI image, `tools/docker/ci/Dockerfile` (`python:3.12-slim-bookworm` pinned by digest, `gettext` pinned, exact
  Python requirements including transitive ones). Every Docker call goes through `tools/docker/run.py`, which tags the
  image with a hash of its whole build context (not only the Dockerfile, so a requirements change also rebuilds),
  always builds and runs `linux/amd64`, mounts the repository at `/repo`, and passes `--user uid:gid` only where the
  host has POSIX ids. Test suites are discovered as `scripts/<suite>/tests` and `tools/<suite>/tests`; module checks
  as the `check` recipe of `scripts/<module>/justfile` or `tools/<module>/justfile` (`tools/ci/suites.py`). Ruff
  lints `scripts/` and `tools/`, excluding the legacy upstream scripts directly in `scripts/`. `CHANGELOG.md` at the
  root carries its rules at its top; this register lives in `wiki/`.
- **The C++ build and the C++ tests (Catch2, `tests/`) run on GitHub CI only.** They need the full dependency build
  (several hours, per OS); no local recipe builds them.
- **Reason.** One command per job, identical for humans, agents and CI, on every host OS. `tools/<suite>/tests` is
  discovered too so the tooling's own tests live next to it.
- **Reverting.** Remove `justfile`, `pyproject.toml`, `tools/docker/`, `tools/ci/`, `tools/repo/`; scripts go back
  to being run by hand.

## D-008 Line endings: LF everywhere, binaries marked

- **Context.** The repository is opened from macOS and Windows over SMB. 20 tracked files were stored with CRLF
  (`text.js`, several web assets, two workflows, `ExPolygon.cpp`, …), which churned on every edit and can break shell
  scripts on macOS.
- **Decision.** `.gitattributes` sets `* text=auto eol=lf` and marks the binary types (`png jpg jpeg gif ico icns 3mf
  stl ttf xlsx dll lib exe`) as `binary`; the CRLF files were renormalised (only line endings changed).
  `tools/repo/tests/test_line_endings.py` fails on any CRLF text file in the tree.
- **Reason.** One line ending for every OS; binary assets never touched by normalisation.
- **Reverting.** Restore the old `.gitattributes` (`* text=auto`) and drop the test.

## D-009 GUI goldens: known gap

- **Context.** The rules require every screen to be pinned to a golden image. No golden suite exists in this
  repository yet. The wxWidgets dialogs touched by the rename can only be captured from a built application, and no
  local C++ build exists (D-007).
- **Decision.** No golden is created by the safe-rename branch. The setup-guide HTML pages (`resources/web/guide/`)
  can be captured without a build; their golden suite is a separate follow-up workstream. Later branches reference
  this entry instead of creating a one-off capture.
- **Reason.** A golden suite needs its own screenshot script, fixtures and Docker capture; bolting a partial one onto a
  text change would not give full coverage.
- **Reverting.** Not applicable: closing the gap means adding the suites.

## Open issues

- **No golden suite** (D-009): wx dialogs need a build; the setup-guide HTML goldens are a follow-up workstream.
- **Merge request links**: CHANGELOG lines of this branch carry `MR: pending` until the request is opened.
