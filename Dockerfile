# ANONYMIZER ROSSILBER — web version (API + page) in one container.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ANONYMIZER_HOST=0.0.0.0 \
    ANONYMIZER_PORT=8080

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# pymorphy2 (used by Natasha) still imports pkg_resources: keep setuptools < 81.
RUN pip install "setuptools<81" \
 && pip install ".[ner,io,web]"

# Models are bundled with the Python packages; the container needs no network.
USER nobody
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/api/health')" || exit 1
CMD ["python", "-m", "anonymizer.web"]
