"""Assistant tool-use loop (M17).

Implements the standard Anthropic tool-use loop with max 6 rounds.
System prompt enforces: numbers from tools only, no safe/unsafe claims,
always mention stated priors.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

from pharmashed_api.assistant.guard import check as guard_check
from pharmashed_api.assistant.tools import TOOL_FN_MAP, TOOL_SCHEMAS

_DEFAULT_MODEL = "claude-sonnet-5"
_TEMPERATURE = 0.2
_MAX_TOKENS = 800
_MAX_TOOL_ROUNDS = 6

_SYSTEM = """\
You are the PharmaShed assistant. You help environmental officers and researchers understand model outputs — you never compute values yourself.

Rules:
1. Every number in your answer must come from a tool result in this turn. Call tools first; never state numbers from memory.
2. Always say that scores and concentrations are "under stated priors" or "under the model's assumed inputs".
3. Never call a stream safe or unsafe. Never say a drug "will not harm" aquatic life. If asked about swimming or drinking water, say the model estimates in-stream concentrations for priority-setting only — it is not a water-quality standard — and point to official monitoring bodies.
4. Use plain language first: "sampling priority score" not just "score", "risk ratio" not just "RQ". Use glossary terms: PEC = predicted concentration, PNEC = no-effect threshold, RQ = risk ratio, λ = leakage, Q = stream flow.
5. Keep answers short (under 200 words unless a table is needed). Use markdown: **bold** key numbers, bullet lists for multiple sites.
6. Mention the `illustrative` status if any provenance entry has status=illustrative or status=todo.
"""

_CORRECTION_PROMPT = (
    "Your previous answer contained numbers that do not appear in the tool results: {unmatched}. "
    "Please revise to use only numbers returned by tools, or explain in words without specific figures."
)


def _call_tool(name: str, args: dict) -> Any:
    fn = TOOL_FN_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name!r}"}
    try:
        return fn(**args)
    except Exception as exc:
        return {"error": str(exc)}


def _extract_links(text: str, tool_calls: list[dict]) -> list[dict]:
    """Produce navigation links from tool calls (for the UI to act on)."""
    links = []
    seen: set[tuple] = set()
    for tc in tool_calls:
        args = tc.get("args", {})
        site_id = args.get("site_id")
        drug = args.get("drug")
        name = tc.get("name", "")

        if site_id and (site_id, drug) not in seen:
            seen.add((site_id, drug))
            label = f"{site_id} — {drug}" if drug else site_id
            target = "Scenarios" if name == "run_scenario" else "Explore"
            links.append({"label": label, "target_tab": target,
                          "site_id": site_id, "drug": drug})
    return links


def run(question: str) -> dict:
    """Run the assistant tool-use loop for one question.

    Args:
        question: the user's question string.

    Returns:
        Dict with answer_markdown, tool_calls, links, guard.
    """
    model = os.environ.get("ASSISTANT_MODEL", _DEFAULT_MODEL)
    client = anthropic.Anthropic()

    messages: list[dict] = [{"role": "user", "content": question}]
    all_tool_calls: list[dict] = []
    all_tool_results: list[Any] = []

    for _ in range(_MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            system=_SYSTEM,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Collect assistant message
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # Final text answer
            answer = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "",
            )
            break

        # Execute tool calls
        tool_results_block = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = _call_tool(block.name, block.input)
            all_tool_calls.append({"name": block.name, "args": block.input})
            all_tool_results.append(result)
            tool_results_block.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results_block})
    else:
        answer = "I was unable to complete the answer within the allowed tool rounds."

    # Guard check
    guard = guard_check(answer, all_tool_results, question)

    # One retry if guard warns
    if guard["status"] == "warn":
        correction = _CORRECTION_PROMPT.format(unmatched=guard["unmatched"])
        messages.append({"role": "user", "content": correction})
        retry = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            system=_SYSTEM,
            messages=messages,
        )
        revised = next(
            (b.text for b in retry.content if hasattr(b, "text")),
            answer,
        )
        guard2 = guard_check(revised, all_tool_results, question)
        if guard2["status"] == "ok":
            answer = revised
            guard = guard2
        else:
            answer = revised
            guard = {"status": "warn", "unmatched": guard2["unmatched"]}

    return {
        "answer_markdown": answer,
        "tool_calls": all_tool_calls,
        "links": _extract_links(answer, all_tool_calls),
        "guard": guard,
    }
