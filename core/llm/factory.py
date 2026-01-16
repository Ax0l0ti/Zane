from abc import ABC, abstractmethod
from typing import Optional


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
