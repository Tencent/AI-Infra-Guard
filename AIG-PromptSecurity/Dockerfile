FROM python:3.12-slim

ENV DEEPEVAL_TELEMETRY_OPT_OUT=YES
ENV DEEPTEAM_TELEMETRY_OPT_OUT=YES

WORKDIR /app/AIG-PromptSecurity

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && (command -v uv >/dev/null 2>&1 || pip install --no-cache-dir uv)

COPY . .

RUN uv sync

CMD ["bash"]