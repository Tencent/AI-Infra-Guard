FROM node:22-bookworm-slim

ARG PI_VERSION=0.73.1
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl python3 socat \
    && npm install --global "@mariozechner/pi-coding-agent@${PI_VERSION}" \
    && groupadd --gid 10001 benchmark \
    && useradd --create-home --uid 10001 --gid 10001 benchmark \
    && groupadd --gid 10002 evaluator \
    && useradd --create-home --uid 10002 --gid 10002 evaluator \
    && rm -rf /var/lib/apt/lists/* /root/.npm

COPY --chown=root:evaluator roguehandoff/__init__.py roguehandoff/catalog.py \
     roguehandoff/store.py roguehandoff/server.py roguehandoff/cli.py \
     /opt/roguehandoff/roguehandoff/
COPY --chown=root:benchmark pi_pending_loader.mjs /opt/agent/session_loader.mjs
COPY --chown=root:benchmark examples/mechanical_agent.py /opt/agent-adapters/mechanical_agent.py
RUN find /opt/roguehandoff -type d -exec chmod 750 {} + \
    && find /opt/roguehandoff -type f -exec chmod 640 {} + \
    && chmod 750 /opt/agent \
    && chmod 640 /opt/agent/session_loader.mjs \
    && chmod 750 /opt/agent-adapters \
    && chmod 550 /opt/agent-adapters/mechanical_agent.py

ENV PYTHONPATH=/opt/roguehandoff
WORKDIR /work
USER evaluator
EXPOSE 8080
ENTRYPOINT ["python3", "-m", "roguehandoff.cli"]
CMD ["serve"]
