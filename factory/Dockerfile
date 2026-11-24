# syntax=docker/dockerfile:1.7
# Railway image for the Agent Factory control plane.
#
# Build context is the repository root so the image also carries the read-only
# xPlan planner (`tools/xplan_dry_run.py`) and the Alpha-Wiki launcher used by
# `reconcile_dry_run`. The factory package remains optional; this image is the
# only place that installs the `harness` extra.
#
# Pins:
#   - dependencies: factory/uv.lock (uv sync --frozen)
#   - uv: 0.11.32
#   - OpenCode CLI: 2.3.0 (must match the auth store copied at runtime)
#   - source: SOURCE_SHA build arg; also recorded as an image label.

FROM python:3.12-slim-bookworm AS opencode

ARG OPENCODE_VERSION=2.3.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl tar \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL https://opencode.ai/v2/install \
      | bash -s -- --version "${OPENCODE_VERSION}" --no-modify-path \
 && /root/.opencode/bin/opencode --version

FROM python:3.12-slim-bookworm AS runtime

ARG SOURCE_SHA=b23a86db04837fa0fe2dae43a103d39b54176fae
ARG OPENCODE_VERSION=2.3.0

LABEL org.opencontainers.image.title="alpha-wiki-agent-factory" \
      org.opencontainers.image.description="Agent Factory control plane (Temporal workers and Harness console)" \
      org.opencontainers.image.revision="${SOURCE_SHA}" \
      org.opencontainers.image.version="0.8.2+factory.0.1.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    HOME=/tmp/home \
    FACTORY_HOME=/tmp/factory \
    FACTORY_PLUGIN_ROOT=/app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git git-lfs openssh-client procps tini \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv==0.11.32

WORKDIR /app/factory

# Dependency layer first: rebuilds only when the lock or manifest changes.
COPY factory/pyproject.toml factory/uv.lock ./
RUN uv sync --frozen --no-dev --extra harness

COPY factory/src ./src
COPY factory/harness ./harness
COPY factory/scripts ./scripts
COPY tools /app/tools
COPY .alpha-wiki /app/.alpha-wiki
COPY AGENTS.md /app/AGENTS.md

COPY factory/docker/lib.sh /usr/local/bin/factory-lib.sh
COPY factory/docker/entrypoint.sh /usr/local/bin/factory-entrypoint
COPY factory/docker/runtime.sh /usr/local/bin/factory-runtime
COPY --from=opencode /root/.opencode/bin/opencode /usr/local/bin/opencode
RUN chmod +x /usr/local/bin/factory-lib.sh /usr/local/bin/factory-entrypoint /usr/local/bin/factory-runtime \
 && mkdir -p /tmp/home \
 && opencode --version

ENV PATH="/app/factory/.venv/bin:${PATH}" \
    PYTHONPATH="/app/factory/src" \
    FACTORY_OPENCODE_BIN="opencode"

ENTRYPOINT ["tini", "--", "/usr/local/bin/factory-entrypoint"]
CMD ["/usr/local/bin/factory-runtime"]
