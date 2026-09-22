FROM node:22-bookworm-slim
ARG CLAUDE_CODE_VERSION=2.1.278
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
COPY model-proxy.py /opt/narness/model-proxy.py
USER node
WORKDIR /workspace
