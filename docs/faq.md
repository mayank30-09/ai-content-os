# Frequently Asked Questions (FAQ) ❓

### Q1: What makes AI Content OS different from LangChain or CrewAI?
AI Content OS is a complete, production-hardened operating system designed specifically for content lifecycle automation. Unlike general-purpose agent frameworks, it comes with 8 pre-built production workers, atomic disk crash checkpointing (`CheckpointManager`), strongly-typed artifact validation (`ArtifactRegistry`), and built-in enterprise observability.

### Q2: How does crash recovery work?
`CheckpointManager` auto-saves an atomic JSON snapshot of the workflow state after every completed worker step. If a server loses power mid-workflow (e.g. at step 4), calling `engine.resume_workflow(workflow_id)` re-hydrates state and resumes execution from step 4 without re-executing steps 1–3.

### Q3: Which AI models are supported?
Google Gemini is the primary active AI provider (`gemini-2.5-flash` / `gemini-2.5-pro`). The architecture's `AIProviderConfig` is designed to support additional LLM providers seamlessly in future releases.

### Q4: Can I add my own custom worker?
Yes! Inherit from `BaseWorker` in `modules/workforce/base_worker.py`, implement `execute(context: WorkflowContext)`, and register your worker with `WorkforceManager`. See **[Examples Index](examples.md)** for code snippets.

---

## ➡️ Next Reading

Explore future planned capabilities in the **[Project Roadmap](roadmap.md)** or read **[Developer Contribution Guide](contributing.md)**.
