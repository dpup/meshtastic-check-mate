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

# Copy files needed for installation
COPY setup.py requirements.txt ./
COPY src ./src/

# Install the package
RUN --mount=type=cache,target=/root/.cache/pip \
  python -m pip install -e .

USER appuser

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 CMD python3 -m checkmate.main --status

ENTRYPOINT ["python3", "-m", "checkmate.main"]