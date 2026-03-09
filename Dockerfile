ARG PYTHON_VERSION=3.12.5
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG UID=10001
RUN adduser \
  --disabled-password \
  --gecos "" \
  --home "/appuser" \
  --shell "/sbin/nologin" \
  --uid "${UID}" \
  appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

USER appuser

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 CMD python3 -m checkmate.main --status

ENTRYPOINT ["uv", "run", "python3", "-m", "checkmate.main"]
