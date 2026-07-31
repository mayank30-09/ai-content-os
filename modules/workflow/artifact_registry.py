"""Artifact Registry module for Workflow Engine subsystem.

Provides a strongly-typed, thread-safe registry abstraction for storing,
retrieving, validating, and serializing workflow artifacts passed between workers.
"""

from typing import Any, TypeVar

from loguru import logger
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ArtifactRegistry:
    """Strongly-typed registry for workflow pipeline artifacts.

    Replaces raw untyped dictionaries with explicit registration, retrieval,
    validation, and serialization methods for Pydantic models and raw dicts.
    """

    def __init__(self, initial_artifacts: dict[str, Any] | None = None) -> None:
        """Initializes ArtifactRegistry with optional initial artifact data.

        Args:
            initial_artifacts: Optional mapping dictionary of artifact_key to data.
        """
        self._registry: dict[str, Any] = {}
        if initial_artifacts:
            for key, val in initial_artifacts.items():
                self.register(key, val)

    def register(self, key: str, artifact: Any) -> None:
        """Registers a typed artifact under the given key.

        Args:
            key: Artifact identifier string.
            artifact: Pydantic model instance, dict, or primitive artifact.
        """
        if not key or not key.strip():
            raise ValueError("Artifact key must be a non-empty string.")
        self._registry[key.strip()] = artifact
        logger.debug(f"ArtifactRegistry: registered artifact under key '{key.strip()}'")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves an artifact by key.

        Args:
            key: Artifact identifier.
            default: Default value if key is not found.

        Returns:
            Artifact object or default value.
        """
        return self._registry.get(key, default)

    def get_typed(self, key: str, model_cls: type[T]) -> T:
        """Retrieves and validates an artifact as a specific Pydantic model type.

        Args:
            key: Artifact identifier.
            model_cls: Expected Pydantic model class.

        Returns:
            Validated Pydantic model instance.

        Raises:
            KeyError: If key is not registered.
            TypeError/ValueError: If artifact cannot be converted to model_cls.
        """
        if key not in self._registry:
            raise KeyError(f"Artifact key '{key}' not found in registry.")

        raw = self._registry[key]
        if isinstance(raw, model_cls):
            return raw
        if isinstance(raw, dict):
            return model_cls.model_validate(raw)
        if isinstance(raw, str):
            return model_cls.model_validate_json(raw)
        raise TypeError(f"Artifact under key '{key}' cannot be converted to {model_cls.__name__}.")

    def contains(self, key: str) -> bool:
        """Checks if key exists in registry.

        Args:
            key: Artifact identifier.

        Returns:
            bool: True if key exists.
        """
        return key in self._registry

    def to_dict(self) -> dict[str, Any]:
        """Serializes all artifacts in the registry into a JSON-compatible dictionary.

        Returns:
            Dictionary mapping artifact keys to JSON data.
        """
        serialized: dict[str, Any] = {}
        for key, val in self._registry.items():
            if isinstance(val, BaseModel):
                serialized[key] = val.model_dump(mode="json")
            else:
                serialized[key] = val
        return serialized

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRegistry":
        """Instantiates an ArtifactRegistry from a serialized dictionary.

        Args:
            data: Serialized artifact dictionary.

        Returns:
            New ArtifactRegistry instance.
        """
        return cls(initial_artifacts=data)

    def __len__(self) -> int:
        return len(self._registry)

    def keys(self) -> list[str]:
        return list(self._registry.keys())

    def all_items(self) -> dict[str, Any]:
        """Returns a shallow copy dictionary of all registered artifacts.

        Returns:
            Dictionary mapping artifact keys to artifact objects.
        """
        return dict(self._registry)
