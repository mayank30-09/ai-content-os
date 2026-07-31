# Developer Guide: Production Docker & Deployment 🐋

Learn how to deploy AI Content OS into production containerized environments.

---

## Multi-Stage Docker Image

Production builds run under non-root system user `appuser:appgroup` (uid 10001):

```dockerfile
# Build command
docker build -t ai-content-os:v0.8.3 -f docker/Dockerfile .
```

---

## Docker Compose Production Setup

Use `deployment/compose/docker-compose.prod.yml`:

```yaml
version: "3.8"
services:
  ai-content-os:
    image: ai-content-os:v0.8.3
    container_name: ai_content_os_prod
    restart: always
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - APP_ENV=production
      - LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 2048M
    ports:
      - "8000:8000"
```

Start container stack:
```bash
docker compose -f deployment/compose/docker-compose.prod.yml up -d
```

---

## ➡️ Next Reading

Explore end-to-end tutorials in **[Single Article Tutorial](../tutorials/01_single_article.md)**.
