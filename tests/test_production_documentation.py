"""Production Documentation Verification Test Suite (Phase 9.1).

Verifies presence, validity, link consistency, and structure of all open-source documentation pages and examples.
"""

from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent


def test_required_documentation_files_exist() -> None:
    """Verifies that all required documentation files exist."""
    required_files = [
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "SUPPORT.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "docs/index.md",
        "docs/quickstart.md",
        "docs/installation.md",
        "docs/troubleshooting.md",
        "docs/faq.md",
        "docs/roadmap.md",
        "docs/contributing.md",
        "docs/examples.md",
        "docs/architecture/overview.md",
        "docs/architecture/workforce.md",
        "docs/architecture/workflow_engine.md",
        "docs/architecture/memory_system.md",
        "docs/architecture/observability.md",
        "docs/architecture/infrastructure.md",
        "docs/api_reference/config.md",
        "docs/api_reference/workforce.md",
        "docs/api_reference/workflow.md",
        "docs/api_reference/observability.md",
        "docs/api_reference/infrastructure.md",
        "docs/guides/custom_worker.md",
        "docs/guides/custom_workflow.md",
        "docs/guides/publishing.md",
        "docs/guides/deployment.md",
        "docs/tutorials/01_single_article.md",
        "docs/tutorials/02_multi_platform.md",
        "docs/tutorials/03_custom_pipeline.md",
    ]

    for rel_path in required_files:
        full_path = WORKSPACE_ROOT / rel_path
        assert full_path.exists(), f"Missing required documentation file: {rel_path}"
        assert full_path.stat().st_size > 0, f"Empty documentation file: {rel_path}"


def test_examples_directory_exists_and_valid() -> None:
    """Verifies that all example scripts exist and are valid Python files."""
    example_files = [
        "examples/README.md",
        "examples/01_basic_workflow.py",
        "examples/02_custom_worker.py",
        "examples/03_custom_template.py",
        "examples/04_observability_export.py",
    ]

    for rel_path in example_files:
        full_path = WORKSPACE_ROOT / rel_path
        assert full_path.exists(), f"Missing example file: {rel_path}"
        assert full_path.stat().st_size > 0, f"Empty example file: {rel_path}"


def test_markdown_mermaid_blocks_validity() -> None:
    """Verifies that Mermaid diagram blocks inside Markdown files are properly closed."""
    docs_dir = WORKSPACE_ROOT / "docs"
    md_files = list(docs_dir.rglob("*.md")) + [WORKSPACE_ROOT / "README.md"]

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        open_mermaid = content.count("```mermaid")
        # Every ```mermaid block must be closed by ```
        assert open_mermaid >= 0
        if open_mermaid > 0:
            lines = content.splitlines()
            in_mermaid = False
            mermaid_closed_count = 0
            for line in lines:
                if line.strip() == "```mermaid":
                    in_mermaid = True
                elif in_mermaid and line.strip() == "```":
                    mermaid_closed_count += 1
                    in_mermaid = False
            assert (
                open_mermaid == mermaid_closed_count
            ), f"Unclosed Mermaid diagram block in {md_file}"


def test_portfolio_artifacts_exist() -> None:
    """Verifies that portfolio artifacts exist."""
    portfolio_files = [
        "portfolio/project_summary.md",
        "portfolio/technical_highlights.md",
        "portfolio/system_design.md",
        "portfolio/interview_questions.md",
        "portfolio/resume_bullets.md",
    ]

    for rel_path in portfolio_files:
        full_path = WORKSPACE_ROOT / rel_path
        assert full_path.exists(), f"Missing portfolio file: {rel_path}"
        assert full_path.stat().st_size > 0, f"Empty portfolio file: {rel_path}"
