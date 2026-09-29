"""Assistant tool-use loop.

Two OpenAI-compatible providers are supported:

* OpenAI (default when OPENAI_API_KEY is set) — model from ASSISTANT_MODEL, default ``gpt-5-mini``.
  GPT-5 models are reasoning models: they take ``max_completion_tokens`` (hidden reasoning tokens
  count against it) and ``reasoning_effort``, and reject a custom ``temperature``.
* Groq (when only GROQ_API_KEY is set) — default ``openai/gpt-oss-120b``.

Set ASSISTANT_PROVIDER=openai|groq to force one. Implements the same max-6-round tool-use loop
and numeric guard for both.
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from pharmashed_api.assistant.guard import check as guard_check
from pharmashed_api.assistant.tools import TOOL_FN_MAP, TOOL_SCHEMAS_OPENAI

_DEFAULT_MODELS = {"openai": "gpt-5-mini", "groq": "openai/gpt-oss-120b"}
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_KEY_ENV = {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY"}
_MAX_TOOL_ROUNDS = 6

# Groq / chat models: plain sampling params.
_GROQ_PARAMS = {"max_tokens": 800, "temperature": 0.2}
# OpenAI reasoning models: no temperature; the token budget must leave room for reasoning.
# Reasoning effort trades speed for care: set ASSISTANT_REASONING_EFFORT to minimal|low|medium|high.
_OPENAI_MAX_COMPLETION_TOKENS = 4000
_DEFAULT_REASONING_EFFORT = "low"

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
    "Rewrite the answer using only numbers returned by tools, or explain in words without specific figures. "
    "Reply with the rewritten answer only: do not mention this correction or apologise."
)


def provider() -> str | None:
    """Which provider will be used, or None if no API key is configured."""
    forced = os.environ.get("ASSISTANT_PROVIDER", "").lower()
    if forced in _KEY_ENV:
        return forced if os.environ.get(_KEY_ENV[forced]) else None
    for name in ("openai", "groq"):
        if os.environ.get(_KEY_ENV[name]):
            return name
    return None


def model_name(prov: str) -> str:
    """Model id for a provider. A leading ``openai/`` is dropped for the OpenAI API itself,
    which uses bare ids (``gpt-5-mini``); the prefixed form is a Groq/gateway convention."""
    model = os.environ.get("ASSISTANT_MODEL") or _DEFAULT_MODELS[prov]
    if prov == "openai" and model.startswith("openai/"):
        model = model.removeprefix("openai/")
    return model


def _client(prov: str) -> OpenAI:
    api_key = os.environ.get(_KEY_ENV[prov])
    if not api_key:
        raise RuntimeError(f"{_KEY_ENV[prov]} not set")
    if prov == "groq":
        return OpenAI(api_key=api_key, base_url=_GROQ_BASE_URL)
    return OpenAI(api_key=api_key)


def _params(prov: str) -> dict:
    if prov == "openai":
        return {
            "max_completion_tokens": _OPENAI_MAX_COMPLETION_TOKENS,
            "reasoning_effort": os.environ.get("ASSISTANT_REASONING_EFFORT") or _DEFAULT_REASONING_EFFORT,
        }
    return dict(_GROQ_PARAMS)


def _context_note(context: dict | None) -> str:
    """System-prompt addendum naming the site/drug the user is looking at in the app."""
    if not context or not context.get("site_id"):
        return ""
    site = context["site_id"]
    drug = context.get("drug")
    where = f"site {site}" + (f" and drug {drug}" if drug else "")
    return (
        f"\nThe user is currently looking at {where} in the app. When they say \"this site\", "
        f"\"here\" or \"it\", they mean that. Still call tools for every number."
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


def run(question: str, context: dict | None = None) -> dict:
    """Run the tool-use loop for one question, optionally about a site/drug the user has open."""
    prov = provider()
    if prov is None:
        raise RuntimeError("No assistant API key configured (OPENAI_API_KEY or GROQ_API_KEY)")
    model = model_name(prov)
    client = _client(prov)
    params = _params(prov)

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM + _context_note(context)},
        {"role": "user", "content": question},
    ]
    all_tool_calls: list[dict] = []
    all_tool_results: list[Any] = []
    answer = ""

    for _ in range(_MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            tools=TOOL_SCHEMAS_OPENAI,
            tool_choice="auto",
            messages=messages,
            **params,
        )

        msg = response.choices[0].message
        finish = response.choices[0].finish_reason

        # Append assistant turn — only include fields the API accepts
        asst_msg: dict = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            asst_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(asst_msg)

        if finish != "tool_calls" or not msg.tool_calls:
            answer = msg.content or ""
            if not answer and finish == "length":
                answer = "The answer was cut off before it finished. Please try again or ask a shorter question."
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
            messages=messages,
            **params,
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
