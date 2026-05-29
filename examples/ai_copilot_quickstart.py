"""AI Copilot quickstart — conversational strategy authoring.

Walks through the full Copilot flow:

    1. Start a new conversation.
    2. Send a goal message and wait for the agent's reply.
    3. Refine over a couple of turns.
    4. Snapshot the conversation context to see what the agent has
       gathered (collected_info, rules, strategy_config).
    5. Optionally save the resulting strategy as a MangroveAI draft.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a new API key (starts with `prod_` for
       production or `local_` for the local dev stack).
    3. Set it as an environment variable:
        export MANGROVE_API_KEY=prod_your_key_here

Run:
    python examples/ai_copilot_quickstart.py
"""
from __future__ import annotations

import textwrap

from mangrove_ai import MangroveAI


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _print_assistant(content: str) -> None:
    # Wrap long lines so the demo output stays readable in a terminal.
    wrapped = textwrap.fill(content, width=78, initial_indent="  ", subsequent_indent="  ")
    print(f"\n[assistant]\n{wrapped}\n")


def main() -> None:
    client = MangroveAI()  # reads MANGROVE_API_KEY from environment

    # ----------------------------------------------------------------
    # 1. Start a new conversation.
    # ----------------------------------------------------------------
    _print_header("1. Starting a new Copilot conversation")
    conv = client.ai_copilot.start_new_conversation()
    print(f"session_id:  {conv.session_id}")
    print(f"thread_id:   {conv.thread_id}")
    print(f"title:       {conv.title}")
    print(f"created_at:  {conv.created_at.isoformat()}")

    # ----------------------------------------------------------------
    # 2. First turn — describe what you want.
    # ----------------------------------------------------------------
    _print_header("2. First turn — describe your goal")
    user_msg = (
        "I want a momentum strategy for ETH on the 1h timeframe. "
        "Keep it simple — one entry trigger, one exit trigger, no filters."
    )
    print(f"\n[user] {user_msg}")
    reply = client.ai_copilot.chat(conv.session_id, user_msg)
    _print_assistant(reply.content)

    # ----------------------------------------------------------------
    # 3. Refine — answer the agent's clarifying questions.
    # ----------------------------------------------------------------
    # State-machine transitions (plan_signals -> assemble_strategy ->
    # backtest -> done) involve reference-strategy retrieval and can
    # legitimately run 60-180s. Default chat() timeout is 180s; bump
    # higher for backtest-heavy turns.
    _print_header("3. Refining — answer the agent's questions")
    user_msg = "MACD bullish cross for entry, MACD bearish cross for exit. Use defaults."
    print(f"\n[user] {user_msg}")
    reply = client.ai_copilot.chat(conv.session_id, user_msg, timeout=240.0)
    _print_assistant(reply.content)

    # ----------------------------------------------------------------
    # 4. Inspect the conversation context — see what the agent collected.
    # ----------------------------------------------------------------
    _print_header("4. Conversation context after refinement")
    ctx = client.ai_copilot.get_conversation(conv.session_id)
    print(f"current_mode:       {ctx.current_mode}")
    print(f"processing_status:  {ctx.processing_status}")
    print(f"message_count:      {len(ctx.conversation_history)}")
    if ctx.collected_info:
        print(f"\ncollected_info:\n  {ctx.collected_info}")
    if ctx.strategy_config:
        print(f"\nstrategy_config draft:")
        for k, v in (ctx.strategy_config or {}).items():
            print(f"  {k}: {v}")

    # ----------------------------------------------------------------
    # 5. Save the strategy as a MangroveAI draft (only if the agent
    #    has fully rendered strategy_config).
    # ----------------------------------------------------------------
    _print_header("5. Save the generated strategy")
    if ctx.strategy_config:
        saved = client.ai_copilot.save_strategy(
            ctx.strategy_config,
            name="ETH 1h MACD momentum (Copilot)",
        )
        if saved.success:
            print(f"saved: {saved.result}")
            print("\nNext steps:")
            print("  - client.strategies.get(<id>)                 # inspect the draft")
            print('  - client.strategies.update_status(<id>, "paper")  # start paper trading')
        else:
            print(f"save failed: {saved.error}")
    else:
        print("strategy_config not yet populated; keep chatting until the")
        print("agent emits a draft, then call save_strategy(ctx.strategy_config).")

    # ----------------------------------------------------------------
    # 6. Optional cleanup — delete the demo conversation.
    # ----------------------------------------------------------------
    _print_header("6. Cleanup")
    client.ai_copilot.delete_conversation(conv.session_id)
    print(f"deleted conversation {conv.session_id}")


if __name__ == "__main__":
    main()
