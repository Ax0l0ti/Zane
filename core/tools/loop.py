"""Tool-use conversation loop.

Handles the multi-turn LLM <-> tool execution cycle:
  1. Send messages + tools to the LLM provider
  2. If response has tool calls, execute them
  3. Append results and call the LLM again
  4. Repeat until end_turn or max iterations reached

Provider-agnostic: message formatting is delegated to the provider.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.llm.types import LLMResponse
from core.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5  # Safety valve: prevent infinite tool loops


@dataclass
class LoopResult:
    """Result of the tool-use conversation loop."""

    text: str = ""            # Final assistant text response
    logs: list = field(default_factory=list)  # LogEvent-compatible dicts
    tool_calls_made: int = 0  # Total number of tool calls executed


def run_tool_loop(
    provider,
    tool_executor: ToolExecutor,
    messages: list[dict],
    tools: list[dict],
    system_prompt: str,
    max_tokens: int = 1024,
    on_log: Optional[Callable[[dict], None]] = None
) -> LoopResult:
    """Run the tool-use conversation loop.

    Calls the LLM, executes any tool_use blocks, feeds results back,
    and repeats until the LLM produces a final text response (end_turn)
    or MAX_TOOL_ITERATIONS is hit.

    Args:
        provider: LLM provider (must support generate_with_tools + format_tool_loop_messages).
        tool_executor: The ToolExecutor to handle tool calls.
        messages: Conversation messages (MUTATED with tool round-trip messages).
        tools: Tool definitions from build_tool_definitions().
        system_prompt: System prompt text.
        max_tokens: Max tokens per LLM call.
        on_log: Optional callback invoked immediately when a log is generated (for streaming).

    Returns:
        LoopResult with the final text, accumulated logs, and tool call count.
    """
    logs = []
    total_tool_calls = 0
    iteration = 0
    collected_text_parts = []
    response: Optional[LLMResponse] = None

    def emit_log(log_dict: dict):
        """Append log and optionally call the callback for streaming."""
        logs.append(log_dict)
        if on_log:
            on_log(log_dict)

    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1

        # Call LLM with tools
        response = provider.generate_with_tools(
            messages=messages,
            tools=tools,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )

        # Collect any text the model produced alongside tool calls
        if response.text:
            collected_text_parts.append(response.text)

        # If no tool calls, we're done
        if not response.has_tool_calls:
            break

        # Execute each tool call and collect results
        tool_call_results = []  # [(tool_call_id, result_json_str)]
        for tc in response.tool_calls:
            total_tool_calls += 1

            emit_log({
                "type": "tool",
                "subtype": "tool_call",
                "message": f"Calling tool: {tc.name}",
                "metadata": {"tool_name": tc.name, "tool_input": tc.input}
            })

            result = tool_executor.execute(tc.name, tc.input)

            # Log the result (truncated for readability)
            result_str = json.dumps(result, default=str)
            result_preview = result_str[:200] + "..." if len(result_str) > 200 else result_str
            emit_log({
                "type": "tool",
                "subtype": "tool_result",
                "message": f"Tool {tc.name} returned: {result_preview}",
                "metadata": {"tool_name": tc.name, "result": result}
            })

            tool_call_results.append((tc.id, result_str))

        # Append assistant + tool result messages in provider-specific format
        round_trip_msgs = provider.format_tool_loop_messages(response, tool_call_results)
        messages.extend(round_trip_msgs)

    else:
        # Hit MAX_TOOL_ITERATIONS
        emit_log({
            "type": "error",
            "subtype": "tool_loop",
            "message": f"Tool loop hit max iterations ({MAX_TOOL_ITERATIONS}). Returning partial response."
        })

    # The final text is the last response.text (or collected parts if partial)
    final_text = ""
    if response and response.text:
        final_text = response.text
    elif collected_text_parts:
        final_text = "\n".join(collected_text_parts)

    if not final_text:
        final_text = "I apologize, but I wasn't able to formulate a response. Could you try rephrasing?"

    return LoopResult(
        text=final_text,
        logs=logs,
        tool_calls_made=total_tool_calls
    )
