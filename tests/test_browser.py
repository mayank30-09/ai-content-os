"""Unit test suite for Browser Foundation module (Milestone 2).

Tests BrowserManager, ProfileManager, SelectorRegistry, BrowserCleanupDaemon, and SessionHealthManager.
"""


import pytest

from modules.browser.daemon import browser_daemon
from modules.browser.manager import browser_manager
from modules.browser.profile_manager import profile_manager
from modules.browser.selector_manager import selector_registry
from modules.browser.session_health import SessionStatus, session_health_mgr


def test_selector_registry_loading_and_fallbacks():
    """Verifies that selectors.json loads correctly and fallback lists are non-empty."""
    assert selector_registry.validate_registry() is True

    gemini_textarea = selector_registry.get_selectors("gemini_web", "prompt_textarea")
    assert isinstance(gemini_textarea, list)
    assert len(gemini_textarea) > 0
    assert "rich-textarea" in gemini_textarea[0] or "div" in gemini_textarea[0] or "textarea" in gemini_textarea[0]

    linkedin_btn = selector_registry.get_selectors("linkedin_web", "start_post_button")
    assert isinstance(linkedin_btn, list)
    assert len(linkedin_btn) > 0

def test_profile_manager_lifecycle():
    """Verifies profile creation, validation, path resolution, and listing."""
    test_profile_name = "test_unit_profile"
    profile_path = profile_manager.create_profile(test_profile_name)

    assert profile_path.exists()
    assert profile_manager.validate_profile(test_profile_name) is True
    assert test_profile_name in profile_manager.list_profiles()

def test_browser_cleanup_daemon_locks(tmp_path):
    """Verifies that the daemon correctly identifies and cleans stale lock files."""
    stale_lock = tmp_path / "SingletonLock"
    stale_lock.write_text("dummy lock content")
    assert stale_lock.exists()

    removed = browser_daemon.cleanup_profile_locks(tmp_path)
    assert removed == 1
    assert not stale_lock.exists()

def test_session_health_manager_cached_status():
    """Verifies default session statuses and cached status accessor."""
    status = session_health_mgr.get_status("gemini_web")
    assert isinstance(status, SessionStatus)

@pytest.mark.asyncio
async def test_browser_manager_startup_shutdown(tmp_path):
    """Verifies BrowserManager start, status query, and graceful stop."""
    test_profile = tmp_path / "test_browser_profile"

    # Start browser manager (headless mode for speed)
    await browser_manager.start(user_data_dir=test_profile, headless=True)
    assert browser_manager.is_running is True

    # Stop browser manager
    await browser_manager.stop()
    assert browser_manager.is_running is False
