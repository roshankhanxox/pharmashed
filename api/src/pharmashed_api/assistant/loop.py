"""Assistant tool-use loop — Groq backend (llama-3.3-70b-versatile).

Uses the OpenAI-compatible client pointed at api.groq.com.
Implements the same max-6-round tool-use loop and numeric guard as before.
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from pharmashed_api.assistant.guard import check as guard_check
from pharmashed_api.assistant.tools import TOOL_FN_MAP, TOOL_SCHEMAS_OPENAI

_DEFAULT_MODEL = "llama-3.3-70b-versatile"
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


def _groq_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _call_tool(name: str, args: dict) -> Any:
    fn = TOOL_FN_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name!r}"}
    try:
        return fn(**args)
    except Exception as exc:
        return {"error": str(exc)}


def _extract_links(text: str, tool_calls: list[dict]) -> list[dict]:
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
    """Run the Groq tool-use loop for one question."""
    model = os.environ.get("ASSISTANT_MODEL", _DEFAULT_MODEL)
    client = _groq_client()

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": question},
    ]
    all_tool_calls: list[dict] = []
    all_tool_results: list[Any] = []
    answer = ""

    for _ in range(_MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            tools=TOOL_SCHEMAS_OPENAI,
            tool_choice="auto",
            messages=messages,
        )

        msg = response.choices[0].message
        finish = response.choices[0].finish_reason

        # Always append the assistant turn
        messages.append(msg.model_dump(exclude_unset=False))

        if finish != "tool_calls" or not msg.tool_calls:
            answer = msg.content or ""
            break

        # Execute each tool call
        tool_results: list[dict] = []
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _call_tool(tc.function.name, args)
            all_tool_calls.append({"name": tc.function.name, "args": args})
            all_tool_results.append(result)
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

        messages.extend(tool_results)
    else:
        answer = "I was unable to complete the answer within the allowed tool rounds."

    # Numeric guard
    guard = guard_check(answer, all_tool_results, question)

    if guard["status"] == "warn":
        correction = _CORRECTION_PROMPT.format(unmatched=guard["unmatched"])
        messages.append({"role": "user", "content": correction})
        retry = client.chat.completions.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            messages=messages,
        )
        revised = retry.choices[0].message.content or answer
        guard2 = guard_check(revised, all_tool_results, question)
        answer = revised
        guard = guard2 if guard2["status"] == "ok" else {"status": "warn", "unmatched": guard2["unmatched"]}

    return {
        "answer_markdown": answer,
        "tool_calls": all_tool_calls,
        "links": _extract_links(answer, all_tool_calls),
        "guard": guard,
    }
