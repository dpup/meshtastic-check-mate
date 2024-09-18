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

RUN --mount=type=cache,target=/root/.cache/pip \
  --mount=type=bind,source=requirements.txt,target=requirements.txt \
  python -m pip install -r requirements.txt

USER appuser
COPY . .

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 CMD python3 check-mate --status

ENTRYPOINT python3 -m check-mate 
