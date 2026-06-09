"""AI Copilot service — conversational strategy authoring.

Surfaces the `/api/v1/ai-copilot/*` endpoints as typed methods. The
Copilot is a stateful OpenAI-backed agent that helps customers go from
"I want to trade momentum on ETH" to a fully-configured MangroveAI
draft strategy.

Async chat: the server returns 202 from `POST /chat/{session_id}` and
processes the LLM call in the background. The blocking ``chat()``
helper polls ``GET /conversations/{session_id}`` until the assistant
message lands. Use ``chat_async()`` if you want to drive the polling
loop yourself.
"""
from __future__ import annotations

import time
from typing import Any

from ..models.ai_copilot import (
    ChatMessage,
    ChatSubmission,
    Configuration,
    Conversation,
    ConversationContext,
    ConversationListResponse,
    ConversationResponse,
    MutationResponse,
    SaveStrategyResponse,
)
from ._base import BaseService

# Default polling parameters for blocking `chat()`. The Copilot is a
# state machine — first-turn (greeting + signal lookup) typically lands
# in 10-20s, but later-turn transitions that fan out to reference-
# strategy retrieval / backtest-summary assembly can run 60-120s under
# load. 180s gives the long tail headroom; callers who need shorter
# fail-fast behavior can pass timeout= explicitly.
_DEFAULT_CHAT_TIMEOUT_SEC = 180.0
_DEFAULT_CHAT_POLL_INTERVAL_SEC = 1.5


class AICopilotService(BaseService):
    """Conversational strategy authoring backed by OpenAI.

    Typical flow:

        client = MangroveAI(api_key="prod_...")

        conv = client.ai_copilot.start_new_conversation()

        reply = client.ai_copilot.chat(
            conv.session_id,
            "I want a momentum strategy for ETH on the 1h timeframe.",
        )
        print(reply.content)

        # Send a few more turns until the agent has gathered the rules,
        # then save the resulting strategy as a MangroveAI draft.
        saved = client.ai_copilot.save_strategy(
            strategy_config={...},  # built from conversation context
            name="ETH momentum",
        )
        print(saved.result)
    """

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #
    def configuration(self) -> Configuration:
        """List the reference artefacts the Copilot has loaded.

        Returns the file names available in the agent's `agentic/`,
        `context/` and `prompts/` directories. Useful when debugging
        why the Copilot doesn't seem to know about a skill or context
        file you expected.
        """
        return self._request_model("GET", "/ai-copilot/configuration", Configuration)

    # ------------------------------------------------------------------ #
    # Conversation lifecycle
    # ------------------------------------------------------------------ #
    def start_new_conversation(self) -> Conversation:
        """Create a fresh conversation session.

        Returns a `Conversation` with a `session_id` you'll pass to
        subsequent `chat()` and `get_conversation()` calls.
        """
        envelope = self._request_model(
            "POST", "/ai-copilot/start_new_conversation", ConversationResponse,
        )
        if not envelope.success or envelope.conversation is None:
            raise RuntimeError(
                f"Failed to create conversation: {envelope.error or 'unknown error'}"
            )
        return envelope.conversation

    def get_latest_conversation(self) -> Conversation | None:
        """Return the most recently created conversation for this user,
        or ``None`` if the user has no conversations yet.
        """
        envelope = self._request_model(
            "GET", "/ai-copilot/get_latest_conversation", ConversationResponse,
        )
        return envelope.conversation

    def list_conversations(self) -> list[Conversation]:
        """List all conversations for this user, newest-first."""
        envelope = self._request_model(
            "GET", "/ai-copilot/list_conversations", ConversationListResponse,
        )
        return envelope.conversations

    def get_conversation(self, session_id: str) -> ConversationContext:
        """Fetch the full working context for a session.

        The response shape depends on ``processing_status``:

        - ``"processing"`` — agent is mid-LLM-call; only
          ``processing_status``, ``message_count`` and ``current_mode``
          are populated. Poll again.
        - ``"complete"`` / ``"idle"`` — full snapshot returned, with
          ``conversation_history`` ready to read.
        """
        return self._request_model(
            "GET", f"/ai-copilot/conversations/{session_id}",
            ConversationContext,
            key="context",
        )

    def delete_conversation(self, session_id: str) -> MutationResponse:
        """Delete a conversation."""
        return self._request_model(
            "DELETE", f"/ai-copilot/conversations/{session_id}",
            MutationResponse,
        )

    def rename_conversation(self, session_id: str, title: str) -> MutationResponse:
        """Rename a conversation."""
        return self._request_model(
            "PUT", f"/ai-copilot/conversations/{session_id}/rename",
            MutationResponse,
            json={"title": title},
        )

    # ------------------------------------------------------------------ #
    # Chat
    # ------------------------------------------------------------------ #
    def chat_async(self, session_id: str, message: str) -> ChatSubmission:
        """Send a message and return the 202 submission immediately.

        The LLM call happens server-side in a background thread. Poll
        `get_conversation(session_id)` until ``processing_status``
        flips to ``"complete"`` — at that point the new assistant turn
        is in ``conversation_history``.

        Prefer ``chat()`` for the simple block-and-wait case.
        """
        return self._request_model(
            "POST", f"/ai-copilot/chat/{session_id}",
            ChatSubmission,
            json={"message": message},
        )

    def chat(
        self,
        session_id: str,
        message: str,
        *,
        timeout: float = _DEFAULT_CHAT_TIMEOUT_SEC,
        poll_interval: float = _DEFAULT_CHAT_POLL_INTERVAL_SEC,
    ) -> ChatMessage:
        """Send a message and block until the assistant responds.

        Submits the message (HTTP 202), then polls the conversation
        context until ``processing_status`` flips back to ``complete``
        / ``idle``. Returns the new assistant turn from
        ``conversation_history``.

        Args:
            session_id: The conversation session UUID.
            message: User message content.
            timeout: Max seconds to wait for the assistant turn.
                Default 180s covers typical Copilot turn latency
                including state-machine transitions; bump higher
                for backtest-heavy turns.
            poll_interval: Seconds between status polls.

        Raises:
            TimeoutError: If no assistant response arrives before
                ``timeout``.
            RuntimeError: If the conversation history shows fewer
                assistant turns after polling than before — indicates
                a server-side error wiping the turn.
        """
        # Snapshot the assistant-turn count BEFORE submitting so we can
        # detect the new turn unambiguously, regardless of whether
        # other clients are also chatting on this session.
        before = self.get_conversation(session_id)
        before_assistant_count = sum(
            1 for m in before.conversation_history if m.role == "assistant"
        )

        # Submit (202 returns immediately).
        self.chat_async(session_id, message)

        # Poll until processing_status == "complete"/"idle" AND the
        # assistant turn count increased.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(poll_interval)
            ctx = self.get_conversation(session_id)

            # When processing, the server returns the slim shape with
            # processing_status set and no full history — keep polling.
            if ctx.processing_status not in {"complete", "idle", None}:
                continue

            assistant_turns = [
                m for m in ctx.conversation_history if m.role == "assistant"
            ]
            if len(assistant_turns) > before_assistant_count:
                return assistant_turns[-1]

        raise TimeoutError(
            f"Copilot chat timed out after {timeout}s waiting for an "
            f"assistant response (session={session_id})."
        )

    # ------------------------------------------------------------------ #
    # Save strategy
    # ------------------------------------------------------------------ #
    def save_strategy(
        self,
        strategy_config: dict[str, Any],
        *,
        name: str | None = None,
    ) -> SaveStrategyResponse:
        """Persist a Copilot-generated strategy as a MangroveAI draft.

        Pulls the rendered ``strategy_config`` out of the conversation
        (typically from ``conversation_context.strategy_config`` after
        a few chat turns) and POSTs it as a new draft strategy. Use
        `client.strategies.update_status(id, "paper")` afterwards to
        start paper-trading it.

        Args:
            strategy_config: Strategy definition dict. Required keys
                vary by Copilot version — at minimum ``asset``,
                ``entry``, ``exit``, ``reward_factor``.
            name: Optional custom name. Defaults to the name embedded
                in ``strategy_config``.
        """
        body: dict[str, Any] = {"strategy_config": strategy_config}
        if name is not None:
            body["name"] = name
        return self._request_model(
            "POST", "/ai-copilot/save_strategy",
            SaveStrategyResponse,
            json=body,
        )
