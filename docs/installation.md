# Installation Guide 🛠️

AI Content OS supports multiple installation strategies: local development with `uv`, containerized execution with Docker & Docker Compose, and production service deployment with `systemd`.

---

## Method 1: Local Development with `uv` (Recommended)

[`uv`](https://docs.astral.sh/uv/) is the primary fast Python package manager for AI Content OS.

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone repository & install environment
git clone https://github.com/mayank30-09/ai-content-os.git
cd ai-content-os
uv sync

# 3. Verify installation with test suite (383 tests)
uv run pytest
```

---

## Method 2: Containerized Execution with Docker

Production multi-stage Docker builds run under a security-hardened non-root user (`appuser:appgroup`).

```bash
# 1. Build Docker image
docker build -t ai-content-os:v0.8.3 -f docker/Dockerfile .

# 2. Run container with environment variables
docker run -d \
  --name ai-content-os \
  -e GEMINI_API_KEY="your_api_key" \
  -e APP_ENV="production" \
  -p 8000:8000 \
  ai-content-os:v0.8.3
```

---

## Method 3: Multi-Container Orchestration with Docker Compose

AI Content OS provides environment-specific compose manifests:

```bash
# Development Environment
docker compose -f deployment/compose/docker-compose.dev.yml up -d

# Staging Environment
docker compose -f deployment/compose/docker-compose.staging.yml up -d

# Production Environment (with resource limits)
docker compose -f deployment/compose/docker-compose.prod.yml up -d
```

---

## Method 4: Production Linux Service with `systemd`

For bare-metal or VM Linux deployments:

1. Create `/etc/systemd/system/ai-content-os.service`:
```ini
[Unit]
Description=AI Content OS Production Service
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/ai-content-os
ExecStart=/root/.cargo/bin/uv run python -m modules.infrastructure.main
Restart=always
RestartSec=5
EnvironmentFile=/etc/ai-content-os/env

[Install]
WantedBy=multi-user.target
```

2. Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-content-os
```

---

## ➡️ Next Reading

Check the **[Troubleshooting Guide](troubleshooting.md)** if you run into configuration errors, or proceed to **[Architecture Overview](architecture/overview.md)**.
