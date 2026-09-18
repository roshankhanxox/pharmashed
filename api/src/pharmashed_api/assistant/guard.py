"""Numeric guard for assistant answers (M17).

Extracts numbers from the final answer and checks each one appears
in the tool results from the same turn (or in the question, or is a
small integer like a rank). On mismatch, signals a retry or warn.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Matches: 1234, 12.34, 1.23e-4, 12%, 12.3%
_NUMBER_RE = re.compile(r"-?\b(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*%?")

# Ranks and common small ints that don't need sourcing
_SMALL_INT_THRESHOLD = 20


def _extract_numbers(text: str) -> set[str]:
    """Extract all numeric strings from text."""
    return set(_NUMBER_RE.findall(text))


def _flatten_json(obj: Any, out: list[float] | None = None) -> list[float]:
    """Recursively collect all numeric values from a JSON-like object."""
    if out is None:
        out = []
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, str):
        for m in _NUMBER_RE.finditer(obj):
            try:
                out.append(float(m.group(1)))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            _flatten_json(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _flatten_json(item, out)
    return out


def _allowed_forms(v: float) -> set[str]:
    """Generate plausible string representations of a value."""
    forms = set()
    forms.add(str(v))
    # Rounded versions 0–4 decimal places
    for d in range(5):
        forms.add(f"{v:.{d}f}")
    # Percentage form (×100)
    pct = v * 100
    for d in range(3):
        forms.add(f"{pct:.{d}f}")
    # Scientific notation
    forms.add(f"{v:.2e}")
    return forms


def check(
    answer: str,
    tool_results: list[Any],
    question: str = "",
) -> dict:
    """Check that every number in answer appears in tool_results or is a small int.

    Args:
        answer: the assistant's final answer text.
        tool_results: list of tool result objects (JSON-serialisable).
        question: the original question (numbers in it are allowed).

    Returns:
        Dict: {status: "ok" | "warn", unmatched: [...]}
    """
    answer_nums = _extract_numbers(answer)
    question_nums = _extract_numbers(question)

    # All numbers from tool results
    all_tool_values = _flatten_json(tool_results)
    allowed_strs: set[str] = set()
    for val in all_tool_values:
        allowed_strs.update(_allowed_forms(val))

    # Also allow numbers that appear in the question
    allowed_strs.update(question_nums)

    unmatched = []
    for num_str in answer_nums:
        # Small integers are always allowed (ranks, counts)
        try:
            as_float = float(num_str)
            if as_float == int(as_float) and 0 <= int(as_float) <= _SMALL_INT_THRESHOLD:
                continue
        except ValueError:
            pass

        if num_str not in allowed_strs:
            # Also check if it matches any allowed string approximately
            matched = any(
                abs(float(num_str) - float(s)) < 1e-6
                for s in allowed_strs
                if _is_numeric(s)
            )
            if not matched:
                unmatched.append(num_str)

    if unmatched:
        return {"status": "warn", "unmatched": unmatched}
    return {"status": "ok", "unmatched": []}


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False
