"""LLM client for JARVIS — HackClub-proxied Nemotron via OpenAI-compatible API.

Responsibilities:
  - Hold the conversation history (rolling N-turn window)
  - Inject the JARVIS system prompt + live PC context on every call
  - Stream the model's user-facing content tokens
  - Run tool calls through core.executor and loop the model on the results
  - Cap tool-call iterations to MAX_TOOL_LOOPS so the model can't lock itself
    in an infinite "call → result → call → ..." cycle

Yielded tokens are ONLY the final user-facing assistant content. Tool calls
and their results are handled internally; the caller (TTS) hears nothing of
them. Tool-call activity IS logged to logs/executor.log + printed via the
on_tool_event callback if supplied.

Usage:
  client = LLMClient()
  for token in client.stream("Open notepad", tools=executor.get_schemas()):
      print(token, end="", flush=True)

Smoke test:
  python -m core.llm --smoke-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import deque
from typing import Any, Callable, Iterator

from openai import OpenAI

from core.config import get_env, load_config, read_text_file
from core.learning import get_store


def _build_lessons_block() -> str:
    """Format the recent-failure summary as a system-prompt section.

    Returns an empty string if there are no recent mistakes, so the prompt
    stays clean on a fresh install.
    """
    try:
        lines = get_store().lessons_for_prompt()
    except Exception:  # noqa: BLE001
        return ""
    if not lines:
        return ""
    body = "\n".join(f"  {l}" for l in lines)
    return (
        "\n\n# Lessons learned from past failures\n"
        "These are mistakes you have made recently across previous conversations. "
        "Do NOT repeat them. If a user request is similar to one of these, take a different approach up front.\n"
        f"{body}\n"
        "(If a tool fails with the same error more than once in this session, "
        "the executor will return a 'learning hint' suggesting what worked last time — pay attention to it.)\n"
    )


MAX_TOOL_LOOPS = 6                  # max LLM↔tool round trips per user turn
MAX_REPEAT_SAME_CALL = 2            # if model emits same (name, args) > N times, bail


class LLMClient:
    """Stateful conversational LLM client backed by HackClub's proxy."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or load_config()
        llm_cfg = cfg["llm"]

        api_key = get_env(llm_cfg["api_key_env"], required=True)
        self.model: str = llm_cfg["model"]
        self.base_url: str = llm_cfg["base_url"]
        self.max_tokens: int = int(llm_cfg["max_tokens"])
        self.temperature: float = float(llm_cfg["temperature"])
        self.history_turns: int = int(llm_cfg["history_turns"])

        self.system_prompt: str = read_text_file(llm_cfg["system_prompt_path"])

        self.client = OpenAI(api_key=api_key, base_url=self.base_url)

        # Each entry is a single chat-completions message dict (the role/content
        # plus any tool_calls / tool_call_id metadata). System prompt is added
        # at send time so we can refresh PC context every turn.
        self._history: deque[dict[str, Any]] = deque(maxlen=self.history_turns * 4)

    # ---- conversation state ----------------------------------------------

    def reset(self) -> None:
        self._history.clear()

    def _build_messages(self, user_text: str, pc_context: str | None) -> list[dict[str, Any]]:
        system = self.system_prompt
        # Inject lessons-learned from the persistent failure store so the model
        # sees its own past mistakes at the start of every turn.
        lessons = _build_lessons_block()
        if lessons:
            system = f"{system}{lessons}"
        if pc_context:
            system = f"{system}\n\n# Live PC context\n{pc_context.strip()}"
        return [
            {"role": "system", "content": system},
            *list(self._history),
            {"role": "user", "content": user_text},
        ]

    # ---- main API --------------------------------------------------------

    def stream(
        self,
        user_text: str,
        *,
        pc_context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        on_tool_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> Iterator[str]:
        """Send `user_text` and yield user-facing tokens of the FINAL reply.

        If `tools` is provided and the model emits tool calls, we execute them
        via core.executor.dispatch, append the results to the message list, and
        re-stream. Only the final post-tool-loop content is yielded to the caller.

        on_tool_event(event_type, payload) — optional hook called with:
          - ("call",   {name, args})   — before each tool dispatch
          - ("result", {name, result}) — after each tool dispatch
        Useful for stdout logging or UI updates.
        """
        # Lazy import so non-tool code paths don't pay the cost of loading every tool module.
        if tools:
            from core import executor as _executor
        else:
            _executor = None

        messages = self._build_messages(user_text, pc_context)
        new_turn_messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]

        # Track every (tool_name, args_str) we've dispatched this turn. If the
        # model retries the SAME call too many times, it's stuck — bail out
        # rather than burn another 4 round trips.
        call_seen_count: dict[tuple[str, str], int] = {}

        for loop_idx in range(MAX_TOOL_LOOPS + 1):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }

            # When tools are in play we DO NOT STREAM. Streamed tool-call
            # arguments are reassembled chunk-by-chunk; HackClub's upstream
            # (DeepInfra / OpenRouter) has a known bug where Python source
            # containing escaped quotes, newlines, or backslashes gets
            # fragmented across chunks and collapses into garbage like
            # {'print(f': 'reated file: {file_path'} . Non-streaming
            # delivers the args as one complete JSON blob — no fragmentation.
            #
            # Without tools (pure conversation), keep streaming for low TTFT.
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
                kwargs["stream"] = False
            else:
                kwargs["stream"] = True

            try:
                response = self.client.chat.completions.create(**kwargs)
            except Exception as e:  # noqa: BLE001
                raise LLMError(f"HackClub request failed: {e}") from e

            content_parts: list[str] = []
            tool_calls_by_index: dict[int, dict[str, Any]] = {}

            if kwargs["stream"]:
                # Streaming path — pure-content turns only.
                for chunk in response:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    piece = getattr(delta, "content", None)
                    if piece:
                        content_parts.append(piece)
            else:
                # Non-streaming path — one complete response. Pull out content
                # and any tool calls from .message in one shot.
                choice = response.choices[0]
                msg = choice.message
                if getattr(msg, "content", None):
                    content_parts.append(msg.content)
                for i, tc in enumerate(getattr(msg, "tool_calls", None) or []):
                    tool_calls_by_index[i] = {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name or "",
                            "arguments": tc.function.arguments or "",
                        },
                    }

            # End of one streamed response. Decide what to do next.
            assembled_tool_calls = [tool_calls_by_index[i] for i in sorted(tool_calls_by_index)]
            assembled_content = "".join(content_parts)

            if not assembled_tool_calls:
                # Plain content reply — yield it (we held it back to be sure),
                # commit to history, return.
                for piece in _chunk_for_yield(assembled_content):
                    yield piece
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": assembled_content,
                }
                new_turn_messages.append(assistant_msg)
                for m in new_turn_messages:
                    # Only persist user/assistant messages to history. Tool messages
                    # are ephemeral — they're only needed within this turn's tool-call
                    # loop. Storing them across turns causes providers like Mistral
                    # to reject the sequence ("Unexpected role 'tool' after 'system'").
                    if m.get("role") != "tool":
                        self._history.append(m)
                return

            # We have tool calls. If we've hit the loop cap, we can't run them —
            # surface that as a spoken error so the user knows.
            if loop_idx == MAX_TOOL_LOOPS:
                msg = (
                    "I hit the tool-call limit before reaching a final answer. "
                    "Try rephrasing or asking me to do one thing at a time."
                )
                for c in _chunk_for_yield(msg):
                    yield c
                new_turn_messages.append({"role": "assistant", "content": msg})
                for m in new_turn_messages:
                    self._history.append(m)
                return

            # Record the assistant's tool-call turn in the message list. Some
            # providers reject `content: null` when tool_calls are present;
            # send an empty string instead when there's no interstitial text.
            assistant_tool_msg: dict[str, Any] = {
                "role": "assistant",
                "content": assembled_content if assembled_content else "",
                "tool_calls": assembled_tool_calls,
            }
            messages.append(assistant_tool_msg)
            new_turn_messages.append(assistant_tool_msg)

            # Execute each tool call, then append a tool-result message per call.
            assert _executor is not None
            for tc in assembled_tool_calls:
                name = (tc["function"]["name"] or "").strip()
                raw_args = tc["function"]["arguments"] or "{}"
                try:
                    parsed_args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    parsed_args = {"_raw": raw_args}

                # Have we seen this exact call before? If repeated too many
                # times, the model is in a doom loop — short-circuit.
                key = (name, raw_args)
                call_seen_count[key] = call_seen_count.get(key, 0) + 1
                if call_seen_count[key] > MAX_REPEAT_SAME_CALL:
                    bail_msg = (
                        f"I'm stuck — I tried the same {name} call repeatedly. "
                        "Try asking me a different way."
                    )
                    for c in _chunk_for_yield(bail_msg):
                        yield c
                    new_turn_messages.append({"role": "assistant", "content": bail_msg})
                    for m in new_turn_messages:
                        self._history.append(m)
                    return

                if on_tool_event:
                    try:
                        on_tool_event("call", {"name": name, "args": parsed_args})
                    except Exception:  # noqa: BLE001 — hook errors don't stop us
                        pass

                result = _executor.dispatch(name, raw_args)

                # Surface the executor's "you've hit this before" hint if any.
                # The executor queues these as it records failures, then we fetch
                # the most recent one and append to the tool result the model sees.
                try:
                    from core.executor import fetch_pending_hint
                    hint = fetch_pending_hint()
                except Exception:  # noqa: BLE001
                    hint = None
                if hint:
                    result = f"{result}{hint}"

                if on_tool_event:
                    try:
                        on_tool_event("result", {"name": name, "result": result})
                    except Exception:  # noqa: BLE001
                        pass

                tool_msg: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": tc.get("id") or f"call_{loop_idx}_{name}",
                    "content": result,
                }
                messages.append(tool_msg)  # needed for current turn's API call
                # new_turn_messages is for cross-turn history — skip tool messages
                # to avoid provider ordering errors (Mistral rejects tool after system).

            # Loop back: model now sees its own tool calls + the results.

        # Loop ended without an explicit return — shouldn't happen, but be safe.
        return

    def complete(self, user_text: str, **kw: Any) -> str:
        """Convenience wrapper — returns the full reply as one string."""
        return "".join(self.stream(user_text, **kw))


class LLMError(RuntimeError):
    """Raised when the LLM provider call fails."""


# ---------------------------------------------------------------------------
# Output post-processing
# ---------------------------------------------------------------------------

_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?!\*)")
_MD_CODE_FENCE = re.compile(r"```[\w]*\n?(.*?)```", re.DOTALL)
_MD_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
_MD_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_LIST_BULLET = re.compile(r"^[\s]*[-*•]\s+", re.MULTILINE)
_MD_LIST_NUM = re.compile(r"^[\s]*\d+\.\s+", re.MULTILINE)


def _strip_markdown(text: str) -> str:
    """Best-effort: remove markdown that the TTS would otherwise read literally.
    Doesn't try to be perfect — just kills the noise (asterisks, backticks,
    leading hashes, bullets). Leaves the words intact."""
    text = _MD_CODE_FENCE.sub(lambda m: m.group(1).strip(), text)
    text = _MD_INLINE_CODE.sub(r"\1", text)
    text = _MD_BOLD.sub(r"\1", text)
    text = _MD_ITALIC.sub(r"\1", text)
    text = _MD_HEADER.sub("", text)
    text = _MD_LIST_BULLET.sub("", text)
    text = _MD_LIST_NUM.sub("", text)
    return text


def _chunk_for_yield(full_text: str, chunk_size: int = 32) -> Iterator[str]:
    """Stream a buffered final reply back to the caller in TTS-friendly chunks.
    Strips markdown noise first."""
    cleaned = _strip_markdown(full_text)
    if not cleaned:
        return
    # Yield in modest chunks so the TTS sentence-splitter still feels streaming.
    for i in range(0, len(cleaned), chunk_size):
        yield cleaned[i:i + chunk_size]


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _smoke_test() -> int:
    print("[smoke] loading config + client...")
    client = LLMClient()
    print(f"[smoke] model    : {client.model}")
    print(f"[smoke] base_url : {client.base_url}")
    print(f"[smoke] sys_chars: {len(client.system_prompt)}")
    print(f"[smoke] sending probe: 'Say JARVIS-ONLINE in five words or less.'")
    print("[smoke] reply    : ", end="", flush=True)

    t0 = time.perf_counter()
    first_token_at: float | None = None
    try:
        for token in client.stream("Say JARVIS-ONLINE in five words or less."):
            if first_token_at is None:
                first_token_at = time.perf_counter() - t0
            sys.stdout.write(token)
            sys.stdout.flush()
    except LLMError as e:
        print(f"\n[smoke] FAILED: {e}")
        return 1
    total = time.perf_counter() - t0

    print()
    print(f"[smoke] first-token latency : {first_token_at:.2f}s" if first_token_at else "[smoke] (no tokens received)")
    print(f"[smoke] total latency       : {total:.2f}s")
    if first_token_at is None:
        print("[smoke] FAILED: no tokens received from server")
        return 1
    print("[smoke] OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS LLM client")
    parser.add_argument("--smoke-test", action="store_true", help="Run end-to-end HackClub smoke test")
    args = parser.parse_args()

    if args.smoke_test:
        raise SystemExit(_smoke_test())
    parser.print_help()


if __name__ == "__main__":
    main()
