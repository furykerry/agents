# Qoder CLI Sandbox Image
# Builds a sandbox-ready image with Qoder CLI and common development tools.

FROM node:20-bookworm

# Install common development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    python3-pip \
    curl \
    jq \
    vim \
    less \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Qoder CLI globally
RUN npm install -g @qoder-ai/qodercli

# Create workspace directory
RUN mkdir -p /workspace

WORKDIR /workspace

# Keep the container running so agent-runtime can operate on it
CMD ["tail", "-f", "/dev/null"]
