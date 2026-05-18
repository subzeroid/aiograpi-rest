FROM python:3.13-slim AS app

ARG GIT_SHA=""
ARG BUILD_TIME=""

LABEL org.opencontainers.image.title="aiograpi-rest" \
      org.opencontainers.image.description="REST API service for aiograpi, the async Instagram Private API client." \
      org.opencontainers.image.source="https://github.com/subzeroid/aiograpi-rest" \
      org.opencontainers.image.url="https://github.com/subzeroid/aiograpi-rest" \
      org.opencontainers.image.documentation="https://subzeroid.github.io/aiograpi-rest/" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_TIME}" \
      org.opencontainers.image.licenses="MIT"

EXPOSE 8000
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_TIME=${BUILD_TIME}
ENV AIOGRAPI_REST_DB_PATH=/data/db.json

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY aiograpi_rest /app/aiograpi_rest
RUN pip install .
COPY . /app/
RUN groupadd --gid 10001 aiograpi \
    && useradd --uid 10001 --gid aiograpi --home-dir /app --shell /usr/sbin/nologin --no-create-home aiograpi \
    && mkdir -p /data \
    && chown -R aiograpi:aiograpi /app /data

CMD ["uvicorn", "aiograpi_rest.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM app AS test

RUN pip install ".[test,docs]"

FROM app AS runtime

USER aiograpi
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()" || exit 1
