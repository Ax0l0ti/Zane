"""Structured response types for the LLM layer.

Separates tool-use response handling from the simple text-in/text-out
interface so generate() stays backward-compatible while
generate_with_tools() returns richer data.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool invocation requested by the LLM."""

    id: str               # e.g. "toolu_abc123" from Claude API
    name: str             # e.g. "execute_skill"
    input: dict[str, Any]  # parsed JSON input from the LLM


@dataclass
class LLMResponse:
    """Structured response from generate_with_tools().

    Attributes:
        text: Concatenated text blocks from the response (may be empty
              if the LLM only produced tool_use blocks).
        tool_calls: List of tool invocations the LLM wants executed.
        stop_reason: "end_turn" when done, "tool_use" when tools requested.
        raw_content: The raw response.content list as dicts, needed
                     for re-sending as assistant message in the tool loop.
    """

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    raw_content: list[dict] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0
