FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCHEAL_DEFAULT_CONFIG=/app/config/default.yaml

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md requirements.lock /app/
COPY config /app/config
COPY demo /app/demo
COPY src /app/src
RUN python -m pip install --upgrade "pip==25.2" \
    && python -m pip install --requirement requirements.lock \
    && python -m pip install --no-deps .

USER 1001:1001
ENTRYPOINT ["python", "-m", "docheal"]
