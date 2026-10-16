"""Mensajes y cliente falsos del SDK para probar sin llamar al modelo."""

from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


def text(content: str) -> TextBlock:
    return TextBlock(text=content)


def agent_call(
    tool_use_id: str, frente: str, encargo: str, tool_name: str = "Agent"
) -> ToolUseBlock:
    """Llamada del coordinador a un subagente (herramienta Agent o su alias Task)."""
    return ToolUseBlock(
        id=tool_use_id,
        name=tool_name,
        input={"subagent_type": frente, "description": f"frente {frente}", "prompt": encargo},
    )


def assistant(*blocks: Any, parent_tool_use_id: str | None = None) -> AssistantMessage:
    return AssistantMessage(
        content=list(blocks), model="fake", parent_tool_use_id=parent_tool_use_id
    )


def tool_result(
    tool_use_id: str, content: str, parent_tool_use_id: str | None = None
) -> UserMessage:
    return UserMessage(
        content=[ToolResultBlock(tool_use_id=tool_use_id, content=content)],
        parent_tool_use_id=parent_tool_use_id,
    )


def result(
    subtype: str = "success",
    stop_reason: str | None = "end_turn",
    terminal_reason: str | None = "completed",
    is_error: bool = False,
) -> ResultMessage:
    return ResultMessage(
        subtype=subtype,
        duration_ms=1,
        duration_api_ms=1,
        is_error=is_error,
        num_turns=1,
        session_id="fake-session",
        stop_reason=stop_reason,
        terminal_reason=terminal_reason,
    )


class FakeClient:
    """Cliente falso: cada `query` consume el siguiente turno preparado."""

    def __init__(self, turns: list[list[Any]], raise_after: Exception | None = None):
        self._turns = list(turns)
        self._raise_after = raise_after  # el SDK lanza tras un ResultMessage de error
        self.queries: list[str] = []
        self.opened = False
        self.closed = False
        self._current: list[Any] = []

    async def __aenter__(self) -> "FakeClient":
        self.opened = True
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        self.closed = True
        return False

    async def query(self, prompt: str, session_id: str = "default") -> None:
        self.queries.append(prompt)
        self._current = self._turns.pop(0)

    async def receive_response(self) -> AsyncIterator[Any]:
        for message in self._current:
            yield message
        if self._raise_after is not None:
            raise self._raise_after


class FakeClientFactory:
    """Fábrica inyectable que cuenta cuántos clientes se crean."""

    def __init__(self, turns: list[list[Any]], raise_after: Exception | None = None):
        self._turns = turns
        self._raise_after = raise_after
        self.created: list[FakeClient] = []
        self.options_received: list[Any] = []

    def __call__(self, options: Any = None) -> FakeClient:
        self.options_received.append(options)
        client = FakeClient(self._turns, self._raise_after)
        self.created.append(client)
        return client
