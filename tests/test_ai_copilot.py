"""Tests for the AICopilotService — conversational strategy authoring."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.models.ai_copilot import (
    ChatMessage,
    ChatSubmission,
    Configuration,
    Conversation,
    ConversationContext,
    MutationResponse,
    SaveStrategyResponse,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


_SESSION_ID = "00000000-0000-0000-0000-000000000abc"
_THREAD_ID = "thread_xyz"
_CREATED_AT = "2026-05-29T12:00:00Z"


def _conversation_payload(session_id: str = _SESSION_ID) -> dict:
    return {
        "session_id": session_id,
        "thread_id": _THREAD_ID,
        "title": "ETH momentum",
        "created_at": _CREATED_AT,
        "working_context": None,
    }


class TestConfiguration:
    def test_returns_typed_response(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/ai-copilot/configuration", json={
            "success": True,
            "agentic_files": ["draft_strategy.md"],
            "context_files": ["signal_library.md"],
            "prompt_files": ["system.md"],
        })
        client = _make_client(mock)

        cfg = client.ai_copilot.configuration()

        assert isinstance(cfg, Configuration)
        assert cfg.success is True
        assert cfg.agentic_files == ["draft_strategy.md"]


class TestConversationLifecycle:
    def test_start_new_conversation_returns_conversation(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/ai-copilot/start_new_conversation", json={
            "success": True,
            "conversation": _conversation_payload(),
        })
        client = _make_client(mock)

        conv = client.ai_copilot.start_new_conversation()

        assert isinstance(conv, Conversation)
        assert conv.session_id == _SESSION_ID
        assert conv.thread_id == _THREAD_ID

    def test_start_new_conversation_raises_on_failure(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/ai-copilot/start_new_conversation", json={
            "success": False,
            "conversation": None,
            "error": "OpenAI quota exceeded",
        })
        client = _make_client(mock)

        with pytest.raises(RuntimeError, match="OpenAI quota exceeded"):
            client.ai_copilot.start_new_conversation()

    def test_get_latest_conversation(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/ai-copilot/get_latest_conversation", json={
            "success": True,
            "conversation": _conversation_payload(),
        })
        client = _make_client(mock)

        conv = client.ai_copilot.get_latest_conversation()

        assert conv is not None
        assert conv.session_id == _SESSION_ID

    def test_get_latest_conversation_when_none_exist(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/ai-copilot/get_latest_conversation", json={
            "success": True,
            "conversation": None,
        })
        client = _make_client(mock)

        assert client.ai_copilot.get_latest_conversation() is None

    def test_list_conversations(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/ai-copilot/list_conversations", json={
            "success": True,
            "conversations": [_conversation_payload(), _conversation_payload("other-id")],
        })
        client = _make_client(mock)

        convs = client.ai_copilot.list_conversations()

        assert len(convs) == 2
        assert convs[0].session_id == _SESSION_ID
        assert convs[1].session_id == "other-id"

    def test_get_conversation_returns_context(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", f"/ai-copilot/conversations/{_SESSION_ID}", json={
            "success": True,
            "context": {
                "session_id": _SESSION_ID,
                "processing_status": "complete",
                "current_mode": "draft_strategy",
                "conversation_history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello!"},
                ],
            },
        })
        client = _make_client(mock)

        ctx = client.ai_copilot.get_conversation(_SESSION_ID)

        assert isinstance(ctx, ConversationContext)
        assert ctx.processing_status == "complete"
        assert len(ctx.conversation_history) == 2
        assert ctx.conversation_history[1].role == "assistant"

    def test_delete_conversation(self) -> None:
        mock = MockTransport()
        mock.add_response("DELETE", f"/ai-copilot/conversations/{_SESSION_ID}", json={
            "success": True,
            "message": "Conversation deleted successfully",
        })
        client = _make_client(mock)

        result = client.ai_copilot.delete_conversation(_SESSION_ID)

        assert isinstance(result, MutationResponse)
        assert result.success is True

    def test_rename_conversation_sends_title(self) -> None:
        mock = MockTransport()
        mock.add_response("PUT", f"/ai-copilot/conversations/{_SESSION_ID}/rename", json={
            "success": True,
            "message": "Conversation renamed successfully",
        })
        client = _make_client(mock)

        result = client.ai_copilot.rename_conversation(_SESSION_ID, "New title")

        assert result.success is True
        recorded = mock.requests[-1]
        assert recorded.json == {"title": "New title"}


class TestChat:
    def test_chat_async_returns_submission(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", f"/ai-copilot/chat/{_SESSION_ID}", json={
            "success": True,
            "data": {
                "status": "processing",
                "session_id": _SESSION_ID,
                "message": "Your message is being processed.",
            },
        })
        client = _make_client(mock)

        submission = client.ai_copilot.chat_async(_SESSION_ID, "Hello")

        assert isinstance(submission, ChatSubmission)
        assert submission.data.status == "processing"
        recorded = mock.requests[-1]
        assert recorded.json == {"message": "Hello"}

    def test_chat_blocks_until_assistant_replies(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The blocking helper takes a snapshot, submits, then polls
        get_conversation until the assistant turn count increases.
        """
        mock = MockTransport()
        mock.add_response("POST", f"/ai-copilot/chat/{_SESSION_ID}", json={
            "success": True,
            "data": {
                "status": "processing",
                "session_id": _SESSION_ID,
                "message": "Your message is being processed.",
            },
        })
        client = _make_client(mock)

        # Sequence the polled conversation states explicitly. The
        # service makes (1) one snapshot call, then (2) submits, then
        # (3) polls until the new assistant turn lands.
        states = iter([
            # snapshot: no assistant turn yet
            ConversationContext(
                session_id=_SESSION_ID,
                processing_status="complete",
                conversation_history=[],
            ),
            # poll 1: processing
            ConversationContext(
                session_id=_SESSION_ID,
                processing_status="processing",
                message_count=1,
            ),
            # poll 2: complete with new assistant turn
            ConversationContext(
                session_id=_SESSION_ID,
                processing_status="complete",
                conversation_history=[
                    ChatMessage(role="user", content="Build me an ETH momentum strategy"),
                    ChatMessage(role="assistant", content="Sure — what timeframe?"),
                ],
            ),
        ])
        monkeypatch.setattr(
            client.ai_copilot, "get_conversation", lambda _sid: next(states)
        )

        reply = client.ai_copilot.chat(
            _SESSION_ID,
            "Build me an ETH momentum strategy",
            timeout=5.0,
            poll_interval=0.01,
        )

        assert isinstance(reply, ChatMessage)
        assert reply.role == "assistant"
        assert reply.content == "Sure — what timeframe?"

    def test_chat_times_out_when_no_assistant_reply(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = MockTransport()
        mock.add_response("POST", f"/ai-copilot/chat/{_SESSION_ID}", json={
            "success": True,
            "data": {
                "status": "processing",
                "session_id": _SESSION_ID,
                "message": "Your message is being processed.",
            },
        })
        client = _make_client(mock)

        # Always return processing — assistant turn never materializes.
        monkeypatch.setattr(
            client.ai_copilot, "get_conversation",
            lambda _sid: ConversationContext(
                session_id=_SESSION_ID,
                processing_status="processing",
                message_count=1,
            ),
        )

        with pytest.raises(TimeoutError, match="timed out"):
            client.ai_copilot.chat(
                _SESSION_ID,
                "Hello",
                timeout=0.1,
                poll_interval=0.01,
            )


class TestSaveStrategy:
    def test_save_strategy_posts_config_and_name(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/ai-copilot/save_strategy", json={
            "success": True,
            "result": {"strategy_id": "strat-abc", "status": "draft"},
        })
        client = _make_client(mock)

        config = {
            "asset": "ETH",
            "entry": [{"name": "macd_bullish_cross", "signal_type": "TRIGGER"}],
            "exit": [{"name": "macd_bearish_cross", "signal_type": "TRIGGER"}],
            "reward_factor": 2.0,
        }
        result = client.ai_copilot.save_strategy(config, name="ETH momentum")

        assert isinstance(result, SaveStrategyResponse)
        assert result.success is True
        assert result.result == {"strategy_id": "strat-abc", "status": "draft"}
        recorded = mock.requests[-1]
        assert recorded.json == {"strategy_config": config, "name": "ETH momentum"}

    def test_save_strategy_without_name(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/ai-copilot/save_strategy", json={
            "success": True,
            "result": {"strategy_id": "strat-xyz"},
        })
        client = _make_client(mock)

        client.ai_copilot.save_strategy({"asset": "BTC"})

        recorded = mock.requests[-1]
        assert recorded.json == {"strategy_config": {"asset": "BTC"}}
        assert "name" not in recorded.json
