# CosmoSlice task runner. `just` lists every recipe; containerised steps run in the pinned CI image
# (tools/docker/ci/Dockerfile) through tools/docker/run.py, so the same command works on every host OS.
# The C++ slicer itself is built and tested by GitHub CI only (see wiki/decision-register.md, D-007).

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

python := if os_family() == "windows" { "python" } else { "python3" }
docker := python + " tools/docker/run.py"

# List every recipe
default:
    @just --justfile "{{justfile()}}" --list

# Build the pinned CI image if its Dockerfile changed, and print its tag
ci-image:
    {{docker}} --build-only

# Run one Python test suite (scripts/<suite>/tests or tools/<suite>/tests), or all of them, in the CI image
test suite="":
    {{docker}} -- python tools/ci/suites.py pytest {{suite}}

# List the discovered Python test suites
suites:
    {{python}} tools/ci/suites.py list

# Lint and format-check the Python tooling with ruff in the CI image
lint:
    {{docker}} -- ruff check scripts tools
    {{docker}} -- ruff format --check scripts tools

# Rewrite the Python tooling with ruff's formatter and safe fixes, in the CI image
fmt:
    {{docker}} -- ruff format scripts tools
    {{docker}} -- ruff check --fix scripts tools

# Rename msgids in place in the pot and every .po from the frozen mapping (scripts/i18n/data/cosmoslice_rename.json)
i18n-rename *args:
    {{python}} scripts/i18n/rename_msgids.py {{args}}

# Check the catalogues (msgfmt --check-format, duplicates) and the product-name guards, in the CI image
i18n-check:
    {{docker}} -- python scripts/i18n/check_catalogs.py
    {{docker}} -- python -m pytest -q scripts/i18n/tests/test_product_name_guard.py

# Show what translators still have to do after the rename, for one language or all
i18n-status lang="":
    {{python}} scripts/i18n/status.py {{lang}}

# Append msgids found in src/ but missing from the pot and every .po (wraps scripts/update_pot.py)
i18n-update-pot:
    {{python}} scripts/update_pot.py --update-po

# Full gate: lint, every test suite, i18n checks, every module `check` recipe (discovered)
ci: lint test i18n-check
    {{python}} tools/ci/suites.py checks --just "{{just_executable()}}"
