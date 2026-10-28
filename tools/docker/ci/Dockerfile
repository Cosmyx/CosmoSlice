# The single CI image of the repository: Python tooling (pytest, ruff), gettext and resvg.
# It is multi-stage ready: other tools are built in their own stage and copied into the final one.
# Always built and run as linux/amd64 through tools/docker/run.py, so every host gets the same bytes.

# resvg renders the brand SVG into PNG and ICNS payloads (scripts/brand_assets, D-010). Pinned by crate version and
# its own Cargo.lock (--locked), built in a digest-pinned Rust image; only the binary reaches the final stage.
FROM rust:1.90-slim-bookworm@sha256:64232e656c058f4468e8d024e990acff04f0fd5a5c0a88a574dc37773d7325c9 AS resvg
RUN cargo install resvg --version 0.48.1 --locked --root /opt/resvg

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext=0.21-12 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-deps -r /tmp/requirements.txt && pip check

COPY --from=resvg /opt/resvg/bin/resvg /usr/local/bin/resvg
