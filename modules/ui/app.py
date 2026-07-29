import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config.settings import settings
from modules.memory.repositories import content_repo
from modules.orchestration.engine import orchestrator
from modules.publisher.linkedin_web import LinkedInWebPublisher

logger = logging.getLogger("AIContentOS.UI")

app = FastAPI(title=settings.APP_NAME)
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    items = content_repo.list_all()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.post("/api/content/create")
async def create_campaign(
    background_tasks: BackgroundTasks,
    topic: str = Form(...),
    format_type: str = Form("multi_format"),
    sources: str | None = Form("")
):
    source_list = [s.strip() for s in sources.split("\n") if s.strip()] if sources else [topic]

    # Run Agent Pipeline in background
    background_tasks.add_task(
        orchestrator.run_content_pipeline,
        topic=topic,
        format_type=format_type,
        sources=source_list
    )

    return HTMLResponse(
        f"""
        <tr>
            <td><strong>{topic}</strong><br><small>Agent pipeline running in background...</small></td>
            <td>{format_type}</td>
            <td><span class="state-tag state-INITIATED">INITIATED</span></td>
            <td>Just now</td>
            <td>Processing...</td>
        </tr>
        """
    )

@app.post("/api/content/{content_id}/approve")
async def approve_and_publish(content_id: str, background_tasks: BackgroundTasks):
    logger.info(f"Human Approval received for content_id: {content_id}")
    content_repo.set_approval(content_id, is_approved=True)

    item = content_repo.get_by_id(content_id)

    # Trigger web publisher in background task
    async def publish_job():
        publisher = LinkedInWebPublisher()
        await publisher.publish(item)

    background_tasks.add_task(publish_job)

    return HTMLResponse(
        f"""
        <tr>
            <td><strong>{item['topic']}</strong></td>
            <td>{item['format_type']}</td>
            <td><span class="state-tag state-APPROVED">APPROVED</span></td>
            <td>{item['created_at'][:16]}</td>
            <td><span style="color: var(--accent-green);">Approved & Publishing</span></td>
        </tr>
        """
    )

@app.post("/api/content/{content_id}/reject")
async def reject_content(content_id: str):
    content_repo.set_approval(content_id, is_approved=False, rejection_reason="User rejected via dashboard")
    item = content_repo.get_by_id(content_id)
    return HTMLResponse(
        f"""
        <tr>
            <td><strong>{item['topic']}</strong></td>
            <td>{item['format_type']}</td>
            <td><span class="state-tag state-FAILED">REJECTED</span></td>
            <td>{item['created_at'][:16]}</td>
            <td><span style="color: var(--accent-red);">Rejected</span></td>
        </tr>
        """
    )
