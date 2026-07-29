"""Workflow state machine module for AI Content OS.

Manages valid state transitions and enforces workflow constraints.
"""

from enum import Enum

from loguru import logger


class ContentState(Enum):
    """Enumeration of content lifecycle states."""
    INITIATED = "INITIATED"
    RESEARCHING = "RESEARCHING"
    AI_GENERATING = "AI_GENERATING"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    PAUSED_FOR_USER = "PAUSED_FOR_USER"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

class StateMachineError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

class WorkflowStateMachine:
    """Enforces state transition rules across content creation lifecycle."""

    VALID_TRANSITIONS = {
        ContentState.INITIATED: [ContentState.RESEARCHING, ContentState.FAILED],
        ContentState.RESEARCHING: [ContentState.AI_GENERATING, ContentState.CAPTCHA_DETECTED, ContentState.FAILED],
        ContentState.AI_GENERATING: [ContentState.PENDING_APPROVAL, ContentState.CAPTCHA_DETECTED, ContentState.FAILED],
        ContentState.CAPTCHA_DETECTED: [ContentState.PAUSED_FOR_USER, ContentState.FAILED],
        ContentState.PAUSED_FOR_USER: [ContentState.RESEARCHING, ContentState.AI_GENERATING, ContentState.PUBLISHING, ContentState.FAILED],
        ContentState.PENDING_APPROVAL: [ContentState.APPROVED, ContentState.FAILED],
        ContentState.APPROVED: [ContentState.PUBLISHING, ContentState.FAILED],
        ContentState.PUBLISHING: [ContentState.PUBLISHED, ContentState.CAPTCHA_DETECTED, ContentState.FAILED],
        ContentState.PUBLISHED: [],
        ContentState.FAILED: [ContentState.INITIATED],
    }

    @classmethod
    def validate_transition(cls, current_state: ContentState, target_state: ContentState) -> bool:
        """Validates if transition from current_state to target_state is allowed."""
        allowed = cls.VALID_TRANSITIONS.get(current_state, [])
        if target_state not in allowed:
            logger.error(f"Invalid state transition attempted: {current_state.value} -> {target_state.value}")
            raise StateMachineError(
                f"Invalid workflow state transition: {current_state.value} -> {target_state.value}"
            )
        logger.debug(f"Validated state transition: {current_state.value} -> {target_state.value}")
        return True

state_machine = WorkflowStateMachine()
