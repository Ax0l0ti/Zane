import json
import os
from typing import Optional

from anthropic import Anthropic
from openai import OpenAI

from .factory import BaseLLM
from .types import LLMResponse, ToolCall


class ClaudeProvider(BaseLLM):
    """Claude LLM provider using the Anthropic API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        """Initialize the Claude provider.

        Args:
            api_key: Anthropic API key. If not provided, reads from
                    ANTHROPIC_API_KEY environment variable.
            model: Model identifier to use.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set it in .env or pass directly."
            )
        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: Optional system prompt for persona/context.
            max_tokens: Maximum tokens in response.

        Returns:
            The generated text response.

        Raises:
            Exception: If the API call fails.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt or "",
            messages=messages
        )
        return response.content[0].text

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> LLMResponse:
        """Generate a response with Claude tool use.

        Args:
            messages: Conversation messages (may contain tool_result blocks).
            tools: Tool definitions in Claude API format.
            system_prompt: Optional system prompt.
            max_tokens: Maximum tokens.

        Returns:
            Parsed LLMResponse with text, tool_calls, and raw_content.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt or "",
            messages=messages,
            tools=tools
        )

        # Parse content blocks into our typed response
        text_parts = []
        tool_calls = []
        raw_content = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                raw_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input
                ))
                raw_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_content=raw_content
        )

    def format_tool_loop_messages(
        self,
        response: LLMResponse,
        tool_call_results: list[tuple[str, str]]
    ) -> list[dict]:
        """Claude format: content blocks for assistant, user message wrapping tool_results."""
        messages = [
            {"role": "assistant", "content": response.raw_content},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tc_id, "content": result}
                for tc_id, result in tool_call_results
            ]}
        ]
        return messages


class OpenAIProvider(BaseLLM):
    """OpenAI LLM provider using the OpenAI API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. If not provided, reads from
                    OPENAI_API_KEY environment variable.
            model: Model identifier to use.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set it in .env or pass directly."
            )
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: Optional system prompt for persona/context.
            max_tokens: Maximum tokens in response.

        Returns:
            The generated text response.

        Raises:
            Exception: If the API call fails.
        """
        # OpenAI uses system message in the messages array
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=full_messages
        )
        return response.choices[0].message.content

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> LLMResponse:
        """Generate a response with OpenAI function calling.

        Converts tool definitions from internal (Claude-like) format to
        OpenAI's function-calling format, then parses the response back
        into the shared LLMResponse type.
        """
        # Build messages with system prompt (copy to avoid mutating caller's list)
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # Build API call kwargs — omit tools param if list is empty
        create_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": full_messages,
        }
        if tools:
            create_kwargs["tools"] = self._convert_tools(tools)

        response = self.client.chat.completions.create(**create_kwargs)

        choice = response.choices[0]
        message = choice.message

        # Parse text and tool calls into our unified types
        text = message.content or ""
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    parsed_input = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    parsed_input = {"_raw": tc.function.arguments}

                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=parsed_input
                ))

        # Normalize stop reasons to match our internal convention
        stop_reason = "tool_use" if choice.finish_reason == "tool_calls" else "end_turn"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_content=[]  # Not needed — format_tool_loop_messages reconstructs from tool_calls
        )

    def format_tool_loop_messages(
        self,
        response: LLMResponse,
        tool_call_results: list[tuple[str, str]]
    ) -> list[dict]:
        """OpenAI format: assistant msg with tool_calls, then individual tool messages."""
        # Reconstruct the assistant message with tool_calls attached
        assistant_msg = {
            "role": "assistant",
            "content": response.text or None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.input)
                    }
                }
                for tc in response.tool_calls
            ]
        }

        # Each tool result is a separate message (OpenAI convention)
        messages = [assistant_msg]
        for tc_id, result in tool_call_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result
            })

        return messages

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[dict]:
        """Convert internal tool definitions (Claude format) to OpenAI function-calling format.

        Internal: {"name": ..., "description": ..., "input_schema": {...}}
        OpenAI:   {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {})
                }
            }
            for tool in tools
        ]
