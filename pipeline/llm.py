"""One Claude call = one agent run. This is the only file that touches the API."""

from __future__ import annotations

import json
import os

from .agents import Agent
from .models import FINDINGS_SCHEMA, Finding

# By default each agent uses the model tier set on it (see agents.py). Set
# AUDIT_MODEL (or pass --model) to force ONE model for every agent instead.
MODEL_OVERRIDE = os.environ.get("AUDIT_MODEL") or None

# Shared, stable instructions + the codebase go here so they cache once and are
# reused across every agent (prompt caching is a prefix match). The per-agent
# focus is the volatile part and rides in the user message, after the cache.
SYSTEM_PREAMBLE = (
    "You are a smart-contract security auditor reviewing the Solidity code below.\n"
    "You will be told one specific bug class to hunt for. Report only concrete, "
    "plausible findings in THAT class — name the contract and function, explain how "
    "it is exploited, and give a fix. Quality over quantity; an empty list is a valid "
    "and good answer when the bug class is absent.\n"
)

_client = None


def _get_client():
    # Imported lazily so `--dry-run` works without the SDK installed.
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


def run_agent(
    agent: Agent,
    codebase: str,
    model_override: str | None = None,
    dry_run: bool = False,
) -> list[Finding]:
    """Run one agent over the codebase and return its findings (tagged with the agent)."""
    if dry_run:
        return []  # the orchestrator prints the plan; no API call is made

    model = model_override or agent.model  # per-agent tier unless overridden
    client = _get_client()
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": f"{SYSTEM_PREAMBLE}\n# Codebase under audit\n{codebase}",
                # Cache the codebase: agents share this prefix, so after the first
                # call the rest read it from cache. (Caching only engages above the
                # model's minimum prefix — a few KB — so tiny demo files won't cache,
                # but a real codebase will. For parallel fan-out, warm the cache with
                # one call before firing the rest.)
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": agent.focus}],
        # Structured outputs: the model must return JSON matching FINDINGS_SCHEMA.
        output_config={"format": {"type": "json_schema", "schema": FINDINGS_SCHEMA}},
    )

    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f"  ! {agent.name}: could not parse model output, skipping")
        return []

    findings = []
    for raw in data.get("findings", []):
        f = Finding(**raw)
        f.found_by = agent.name
        findings.append(f)
    return findings
