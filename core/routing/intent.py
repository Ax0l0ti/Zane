from typing import Literal, Optional

from pydantic import BaseModel, Field


class Intent(BaseModel):
    """Router intent classification result.

    Used by core/routing/detector.py to decide the next step.
    """
    mode: Literal["CHAT", "SKILL", "DEV"] = Field(
        ...,
        description="The operating mode: CHAT for conversation, SKILL for tool use, DEV for code generation"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )
    skill_name: Optional[str] = Field(
        None,
        description="Target skill name if mode is SKILL"
    )
    project_context: Optional[str] = Field(
        None,
        description="Active project name if relevant"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Brief explanation of why this intent was detected"
    )
