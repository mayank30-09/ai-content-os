import logging
from enum import Enum

logger = logging.getLogger("AIContentOS.StateMachine")

class ContentState(Enum):
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
    pass

class WorkflowStateMachine:
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
        ContentState.FAILED: [ContentState.INITIATED]  # Retry support
    }

    @classmethod
    def validate_transition(cls, current_state: ContentState, target_state: ContentState) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(current_state, [])
        if target_state not in allowed:
            raise StateMachineError(
                f"Invalid workflow state transition: {current_state.value} -> {target_state.value}"
            )
        return True

state_machine = WorkflowStateMachine()
