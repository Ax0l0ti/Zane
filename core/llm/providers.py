import os
from typing import Optional

from anthropic import Anthropic
from openai import OpenAI

from .factory import BaseLLM


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
