"""Models for the AI Copilot — conversational strategy authoring.

Wraps the `/api/v1/ai-copilot/*` surface. The Copilot is a stateful chat
agent backed by OpenAI. Customers start a conversation, send messages,
and (when the agent has gathered enough context) save the generated
strategy to MangroveAI as a draft.

Chat is asynchronous server-side — `POST /chat/{session_id}` returns 202
immediately, then the LLM call happens in a background thread. Callers
poll `GET /conversations/{session_id}` until ``processing_status``
flips back to ``complete``. The blocking `client.ai_copilot.chat()`
helper hides that dance; `chat_async()` exposes it for callers that
want to do their own polling.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ._base import MangroveModel


# ---------------------------------------------------------------------------
# Conversation lifecycle
# ---------------------------------------------------------------------------


class Conversation(MangroveModel):
    """One Copilot conversation session.

    A conversation is a persistent OpenAI thread plus the agent's local
    working context (current mode, collected info, etc.). Survives across
    requests; can be resumed by `session_id`.
    """

    session_id: str
    thread_id: str
    title: str
    created_at: datetime
    working_context: dict[str, Any] | None = None


class ConversationResponse(MangroveModel):
    """Envelope returned by create / get-latest / get-by-id endpoints."""

    success: bool
    conversation: Conversation | None = None
    error: str | None = None


class ConversationListResponse(MangroveModel):
    """Envelope for `list_conversations`."""

    success: bool
    conversations: list[Conversation] = []


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatMessage(MangroveModel):
    """One message inside a conversation history.

    ``role`` is ``"user"`` or ``"assistant"``. The Copilot also emits
    tool-call shapes inside ``content`` (JSON blocks the agent renders);
    the SDK surfaces those verbatim — parse them yourself if needed.
    """

    role: str
    content: str


class ChatSubmissionData(MangroveModel):
    """The 202 body's ``data`` field from `POST /chat/{session_id}`."""

    status: str  # "processing"
    session_id: str
    message: str  # human-readable "Your message is being processed..."


class ChatSubmission(MangroveModel):
    """Raw 202 Accepted response shape from the async chat endpoint."""

    success: bool
    data: ChatSubmissionData


class ConversationContext(MangroveModel):
    """Full working context for a session as returned by
    ``GET /conversations/{session_id}``.

    When the agent is mid-LLM-call, only ``processing_status``,
    ``message_count`` and ``current_mode`` are populated. When idle
    (``processing_status == "complete"`` / ``"idle"``), the full
    snapshot is returned with `conversation_history` ready to read.
    """

    session_id: str | None = None
    org_id: str | None = None
    user_id: str | None = None
    strategy_id: str | None = None
    current_mode: str | None = None
    processing_status: str | None = None
    message_count: int | None = None
    conversation_history: list[ChatMessage] = []
    collected_info: dict[str, Any] | None = None
    rules: dict[str, Any] | None = None
    strategy_config: dict[str, Any] | None = None
    backtest_id: str | None = None
    backtest_status: str | None = None
    backtest_results: dict[str, Any] | None = None
    llm_response_metadata: dict[str, Any] | None = None
    token_estimates: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Save strategy
# ---------------------------------------------------------------------------


class SaveStrategyResponse(MangroveModel):
    """Result of `POST /save_strategy` — `result` shape includes the
    new MangroveAI strategy_id once the draft is persisted.
    """

    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Configuration (reference artefacts)
# ---------------------------------------------------------------------------


class Configuration(MangroveModel):
    """Lists the agentic / context / prompt files the Copilot has loaded."""

    success: bool
    agentic_files: list[str] = []
    context_files: list[str] = []
    prompt_files: list[str] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Mutation responses
# ---------------------------------------------------------------------------


class MutationResponse(MangroveModel):
    """Envelope for rename / delete endpoints."""

    success: bool
    message: str | None = None
    error: str | None = None
