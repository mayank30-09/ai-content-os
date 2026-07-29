"""Profile manager module for AI Content OS.

Manages creation, loading, validation, and directory path helpers for browser
user data profiles (cookies, session state, local storage).
"""

from pathlib import Path

from loguru import logger

from config.settings import settings


class ProfileManager:
    """Manages browser user profile storage directories."""

    def __init__(self, base_profiles_dir: Path = settings.BROWSER_PROFILES_DIR):
        self.base_profiles_dir = base_profiles_dir
        self.base_profiles_dir.mkdir(parents=True, exist_ok=True)

    def get_profile_path(self, profile_name: str) -> Path:
        """Returns the absolute path to a profile directory."""
        clean_name = profile_name.strip().lower().replace(" ", "_")
        return self.base_profiles_dir / clean_name

    def create_profile(self, profile_name: str) -> Path:
        """Creates a new browser profile directory if it does not exist.

        Args:
            profile_name: Identifier name for the browser profile.

        Returns:
            Path: Absolute path to created profile directory.
        """
        profile_path = self.get_profile_path(profile_name)
        if not profile_path.exists():
            profile_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created new browser profile directory: '{profile_path}'")
        else:
            logger.debug(f"Profile directory already exists: '{profile_path}'")
        return profile_path

    def validate_profile(self, profile_name: str) -> bool:
        """Validates that a profile directory exists and is accessible.

        Args:
            profile_name: Identifier name for the browser profile.

        Returns:
            bool: True if profile path exists and is writable, False otherwise.
        """
        profile_path = self.get_profile_path(profile_name)
        if not profile_path.exists() or not profile_path.is_dir():
            logger.warning(f"Profile validation failed: Path '{profile_path}' does not exist or is not a directory.")
            return False

        # Verify write permission
        test_file = profile_path / ".perm_check"
        try:
            with open(test_file, "w") as f:
                f.write("check")
            test_file.unlink(missing_ok=True)
            logger.debug(f"Profile directory validation successful: '{profile_path}'")
            return True
        except Exception as e:
            logger.error(f"Profile permission check failed for '{profile_path}': {e}")
            return False

    def list_profiles(self) -> list[str]:
        """Lists all existing profile names in the base directory."""
        if not self.base_profiles_dir.exists():
            return []
        return [
            p.name for p in self.base_profiles_dir.iterdir() if p.is_dir()
        ]

profile_manager = ProfileManager()
