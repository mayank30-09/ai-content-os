# Developer Guide: Multi-Platform Publishing 📢

Configure automated publishing targets for LinkedIn, X (Twitter), and CMS platforms under `PublisherWorker`.

---

## Configuration

Set platform target credentials using environment variables:

```bash
export LINKEDIN_CLIENT_ID="linkedin_app_id"
export LINKEDIN_CLIENT_SECRET="linkedin_secret"
export X_API_KEY="x_api_key_string"
export X_API_SECRET="x_api_secret_string"
```

In your `WorkflowRequest`, specify the desired target platforms:

```python
request = WorkflowRequest(
    topic="Enterprise Microservices with Python 3.14",
    target_platforms=["linkedin", "twitter", "cms"]
)
```

`PublisherWorker` will assemble platform-tailored payloads and return a `PublicationPackage`.

---

## ➡️ Next Reading

Read the **[Deployment Guide](deployment.md)**.
