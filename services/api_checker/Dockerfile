FROM docker.io/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AIG_API_CHECKER_ROOT_PATH=/api-checker \
    AIG_API_CHECKER_DATA_DIR=/data \
    AIG_API_CHECKER_LOG_LEVEL=INFO

WORKDIR /app

COPY services/api_checker/requirements.txt /tmp/api-checker-requirements.txt
RUN pip install --no-cache-dir -r /tmp/api-checker-requirements.txt \
    && rm /tmp/api-checker-requirements.txt

COPY services/__init__.py /app/services/__init__.py
COPY services/api_checker /app/services/api_checker

RUN mkdir -p /data \
    && addgroup --system aig \
    && adduser --system --ingroup aig --home /nonexistent --no-create-home aig \
    && chown -R aig:aig /app /data

USER aig

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()"]

CMD ["python", "-m", "uvicorn", "services.api_checker.server:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
