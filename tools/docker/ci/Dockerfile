# The single CI image of the repository: Python tooling (pytest, ruff) and gettext.
# It is multi-stage ready: other tools are built in their own stage and copied into the final one.
# Always built and run as linux/amd64 through tools/docker/run.py, so every host gets the same bytes.
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
