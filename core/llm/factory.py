from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .types import LLMResponse


class BaseLLM(ABC):
    """Abstract base class for LLM providers.

    All LLM implementations must inherit from this class and implement
    the generate method. This ensures provider-agnostic code in the rest
    of the application.
    """

    @abstractmethod
    def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Roles should be 'user' or 'assistant'.
            system_prompt: Optional system prompt to set context/persona.
            max_tokens: Maximum tokens in the response.

        Returns:
            The generated text response.

        Raises:
            Exception: If the API call fails.
        """
        pass

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> "LLMResponse":
        """Generate a response with tool-use capability.

        Args:
            messages: List of message dicts (supports mixed content blocks).
            tools: List of tool definition dicts with name, description, input_schema.
            system_prompt: Optional system prompt.
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse with text, tool_calls, stop_reason, and raw_content.

        Raises:
            NotImplementedError: If the provider doesn't support tool use.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support tool use."
        )

    def format_tool_loop_messages(
        self,
        response: "LLMResponse",
        tool_call_results: list[tuple[str, str]]
    ) -> list[dict]:
        """Build messages to append for a tool loop round-trip.

        Each provider formats assistant + tool result messages differently.
        Claude uses content blocks; OpenAI uses separate tool messages.

        Args:
            response: The LLM response containing tool calls.
            tool_call_results: List of (tool_call_id, result_json_str) tuples.

        Returns:
            List of message dicts to append to the conversation.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement format_tool_loop_messages."
        )
