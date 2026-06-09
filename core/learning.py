"""Failure memory + lessons-learned injection for Lumi.

The system is small but does three things:

1. RECORD — every tool failure is appended to logs/learning/mistakes.jsonl
   with (tool_name, args_signature, error_signature, error_message, turn_id, ts).
   Signatures are short hashes so we don't bloat memory with raw payloads.

2. HINT — when the executor is about to return an error, we check how many
   times this exact (tool, error_class) has failed in recent history. If >= 2,
   we append a "you've hit this before" hint to the error string the model
   sees, including any successful workarounds we've previously observed for
   the same tool+error.

3. PROMPT — on every LLM turn, we read the most recent N unique (tool, error_class)
   pairs and inject them as a "Lessons learned from past failures" section
   near the top of the system prompt. This means Lumi sees its own past
   mistakes at the start of every turn, not just when it triggers one.

File format: newline-delimited JSON. One record per line. Easy to grep,
truncate, back up, or move to a real DB later.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT


# ============================================================================
# Constants
# ============================================================================

LEARN_DIR = PROJECT_ROOT / "logs" / "learning"
MISTAKES_PATH = LEARN_DIR / "mistakes.jsonl"
SUCCESSES_PATH = LEARN_DIR / "successes.jsonl"

# How many recent unique (tool, error_class) pairs to surface in the prompt
PROMPT_LESSON_LIMIT = 6
# How many historical hits before we tag a failure as "you've seen this before"
REPEAT_FAILURE_THRESHOLD = 2
# Don't look back further than this many days in any aggregation
HISTORY_WINDOW_DAYS = 30


# ============================================================================
# Records
# ============================================================================

@dataclass
class Mistake:
    tool: str
    args_signature: str
    error_signature: str
    error_message: str
    turn_id: str
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class Success:
    tool: str
    args_signature: str
    turn_id: str
    note: str = ""
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


# ============================================================================
# Signature helpers
# ============================================================================

_ARG_NORMALIZE_RE = re.compile(r"\s+")


def _sig_args(args: dict[str, Any] | None) -> str:
    """Stable short hash of the args dict, with whitespace and case normalized.

    We don't store the raw code string (could be huge) — we store its hash
    so the same broken attempt is recognized as 'the same mistake' later.
    """
    if not args:
        return "noargs"
    norm = {k: _ARG_NORMALIZE_RE.sub(" ", str(v).strip().lower()) for k, v in sorted(args.items())}
    blob = json.dumps(norm, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


_SAFE_ERR_RE = re.compile(r"[^a-z0-9 _:/.\-]+")
_WS_RE = re.compile(r"\s+")


def _sig_error(error_message: str) -> str:
    """Class-level error signature: strip traceback noise, hash the meaningful part.

    Goal: 'IndentationError: expected an indented block' on line 11 vs line 12
    counts as the SAME error_class, not different ones. We keep the error
    type name and the first sentence of the message, drop line numbers.
    """
    msg = error_message or "unknown"
    # Take first line / first sentence
    msg = msg.split("\n", 1)[0].split(".", 1)[0]
    # Drop line/column numbers ("line 11", "column 3", "(<lumi-run_python>, line 9)")
    msg = re.sub(r"\(?<[^>]+>,\s*line\s+\d+\)?", "", msg)
    msg = re.sub(r"\bline\s+\d+\b", "", msg, flags=re.IGNORECASE)
    msg = _SAFE_ERR_RE.sub(" ", msg)
    msg = _WS_RE.sub(" ", msg).strip().lower()
    return hashlib.sha1(msg.encode("utf-8")).hexdigest()[:10]


# ============================================================================
# Store (singleton per process)
# ============================================================================

class LearningStore:
    """Persistent store of past failures + successful workarounds."""

    def __init__(self) -> None:
        LEARN_DIR.mkdir(parents=True, exist_ok=True)
        # Load in memory on startup so prompt-injection is fast
        self._mistakes: list[Mistake] = self._read_jsonl(MISTAKES_PATH, Mistake)
        self._successes: list[Success] = self._read_jsonl(SUCCESSES_PATH, Success)
        # Index: (tool, error_sig) -> [Mistake, Mistake, ...]
        self._mistake_index: dict[tuple[str, str], list[Mistake]] = defaultdict(list)
        for m in self._mistakes:
            self._mistake_index[(m.tool, m.error_signature)].append(m)

    @staticmethod
    def _read_jsonl(path: Path, cls: type) -> list[Any]:
        out: list[Any] = []
        if not path.exists():
            return out
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        out.append(cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__}))
                    except (json.JSONDecodeError, TypeError):
                        continue    # skip corrupt lines; never crash the app
        except OSError:
            pass
        return out

    def _append_jsonl(self, path: Path, record: Any) -> None:
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(record.to_json() + "\n")
        except OSError as e:    # noqa: BLE001
            print(f"[learning] WARNING: could not append to {path}: {e}")

    # ---- Recording ----

    def record_mistake(
        self,
        *,
        tool: str,
        args: dict[str, Any] | None,
        error_message: str,
        turn_id: str = "",
    ) -> Mistake:
        m = Mistake(
            tool=tool,
            args_signature=_sig_args(args),
            error_signature=_sig_error(error_message),
            error_message=(error_message or "")[:500],
            turn_id=turn_id,
        )
        self._mistakes.append(m)
        self._mistake_index[(m.tool, m.error_signature)].append(m)
        self._append_jsonl(MISTAKES_PATH, m)
        return m

    def record_success(self, *, tool: str, args: dict[str, Any] | None, turn_id: str = "", note: str = "") -> Success:
        s = Success(
            tool=tool,
            args_signature=_sig_args(args),
            turn_id=turn_id,
            note=note[:200],
        )
        self._successes.append(s)
        self._append_jsonl(SUCCESSES_PATH, s)
        return s

    # ---- Reading ----

    def count_recent(
        self,
        *,
        tool: str,
        error_signature: str,
        since_days: int = HISTORY_WINDOW_DAYS,
    ) -> int:
        """How many times have we seen this (tool, error) recently?"""
        cutoff = time.time() - since_days * 86400
        return sum(1 for m in self._mistake_index.get((tool, error_signature), [])
                   if m.ts >= cutoff)

    def last_success_for(
        self,
        *,
        tool: str,
        error_signature: str,
        since_days: int = HISTORY_WINDOW_DAYS,
    ) -> Success | None:
        """Find the most recent successful invocation of `tool` that came after
        a (tool, error_signature) failure — i.e. a recovered-from-mistake success.

        We use this to suggest 'here's what worked last time' hints.
        """
        # Find last failure time for this combo
        failures = [m for m in self._mistake_index.get((tool, error_signature), [])
                    if m.ts >= time.time() - since_days * 86400]
        if not failures:
            return None
        last_failure_ts = max(m.ts for m in failures)
        # Find first success of `tool` after that
        for s in reversed(self._successes):
            if s.tool == tool and s.ts > last_failure_ts:
                return s
        return None

    def lessons_for_prompt(self, limit: int = PROMPT_LESSON_LIMIT) -> list[str]:
        """Return human-readable bullet lines summarizing recent unique failure classes.

        Used to inject into the system prompt each turn so the model sees
        what it has screwed up before, not just at the moment of the screw-up.
        """
        # Count recent failures by (tool, error_signature, error_message)
        cutoff = time.time() - HISTORY_WINDOW_DAYS * 86400
        recent = [m for m in self._mistakes if m.ts >= cutoff]

        # Group by (tool, error_signature) and find the most representative
        # error_message and a count.
        grouped: dict[tuple[str, str], list[Mistake]] = defaultdict(list)
        for m in recent:
            grouped[(m.tool, m.error_signature)].append(m)

        ranked: list[tuple[int, str, str, str]] = []
        for (tool, err_sig), items in grouped.items():
            # Most recent error_message for this group, prefixed by count
            items.sort(key=lambda m: m.ts)
            last_msg = items[-1].error_message.strip().split("\n", 1)[0]
            if len(last_msg) > 140:
                last_msg = last_msg[:140] + "..."
            ranked.append((len(items), tool, err_sig, last_msg))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        return [
            f"- {tool} has failed {count}x recently: {msg}"
            for count, tool, err_sig, msg in ranked[:limit]
        ]

    def hint_for_failure(
        self,
        *,
        tool: str,
        error_message: str,
        args: dict[str, Any] | None,
    ) -> str | None:
        """If this exact error class has happened >= REPEAT_FAILURE_THRESHOLD times
        recently, return a hint string to append to the error message the model sees.
        Returns None if no hint is warranted.
        """
        err_sig = _sig_error(error_message)
        count = self.count_recent(tool=tool, error_signature=err_sig)
        # We only get asked for a hint AFTER the failure has already been recorded,
        # so `count` includes the current one. We want the hint to appear on the
        # REPEAT_FAILURE_THRESHOLD'th and onward (e.g. threshold=2 → hint on
        # the 2nd, 3rd, 4th... occurrence of this error class).
        if count < REPEAT_FAILURE_THRESHOLD:
            return None
        hint = (
            f"\n\n[learning hint] You've hit this {tool} error {count} times "
            f"in recent sessions. Try a different approach: "
        )
        last_success = self.last_success_for(tool=tool, error_signature=err_sig)
        if last_success and last_success.note:
            hint += f"last time you succeeded with: {last_success.note}. "
        else:
            hint += (
                "review the tool's description and constraints, simplify the args, "
                "or call a different tool entirely."
            )
        return hint


# ============================================================================
# Singleton accessor
# ============================================================================

_store: LearningStore | None = None


def get_store() -> LearningStore:
    global _store
    if _store is None:
        _store = LearningStore()
    return _store


# ============================================================================
# CLI for inspecting what Lumi has learned
# ============================================================================

def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Lumi failure memory")
    p.add_argument("--show", action="store_true", help="Show current lessons + recent mistakes")
    p.add_argument("--tail", type=int, default=20, help="How many recent mistake records to show")
    p.add_argument("--reset", action="store_true", help="Wipe the mistake log (irreversible)")
    args = p.parse_args()

    store = get_store()
    if args.reset:
        MISTAKES_PATH.unlink(missing_ok=True)
        SUCCESSES_PATH.unlink(missing_ok=True)
        print("[learning] wiped mistakes + successes logs")
        return

    print(f"[learning] {len(store._mistakes)} mistakes, {len(store._successes)} successes on record")
    print()
    print("Lessons currently injected into the system prompt:")
    for line in store.lessons_for_prompt():
        print(f"  {line}")
    if not store.lessons_for_prompt():
        print("  (none yet)")

    if args.tail:
        print()
        print(f"Last {min(args.tail, len(store._mistakes))} mistakes:")
        for m in store._mistakes[-args.tail:]:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.ts))
            print(f"  {ts}  {m.tool}  err={m.error_signature}  args={m.args_signature}")
            print(f"      {m.error_message[:120]}")


if __name__ == "__main__":
    main()
