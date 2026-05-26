"""Fan out to the agents, then merge and de-duplicate their findings."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from .agents import AGENTS, Agent
from .llm import MODEL_OVERRIDE, run_agent
from .models import Finding


def audit(
    codebase: str,
    model_override: str | None = None,
    agents: list[Agent] = AGENTS,
    parallel: bool = True,
    on_done: Callable[[Agent, list[Finding]], None] | None = None,
) -> list[Finding]:
    """Run every agent over the codebase and return merged, de-duplicated findings.

    Each agent uses its own model tier (agents.py) unless `model_override` (or the
    AUDIT_MODEL env var) forces one model for all of them. `on_done(agent, findings)`
    is called as each agent finishes — used for the live scan log.
    """
    override = model_override or MODEL_OVERRIDE
    raw: list[Finding] = []

    if parallel:
        # Fan out; report each agent as it finishes (completion order, no print races).
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            futures = {pool.submit(run_agent, a, codebase, override): a for a in agents}
            for fut in as_completed(futures):
                agent = futures[fut]
                findings = fut.result()
                if on_done:
                    on_done(agent, findings)
                raw.extend(findings)
    else:
        for agent in agents:
            findings = run_agent(agent, codebase, override)
            if on_done:
                on_done(agent, findings)
            raw.extend(findings)

    return _merge(raw)


def _merge(findings: list[Finding]) -> list[Finding]:
    """Collapse near-duplicate findings on the same spot; track multi-agent confirmation.

    Caveat: the key is dumb — it dedups on (contract, location) as lowercased strings. Two
    agents describing the same root cause in different words, or pinning slightly different
    line ranges, will NOT merge. That's deliberate: over-merging silently hides bugs, and
    eyeballing two near-duplicates beats losing one. A semantic merge (cluster by root cause)
    is the obvious upgrade if you want it.
    """
    merged: dict[tuple[str, str], Finding] = {}
    for f in findings:
        key = (f.contract.strip().lower(), f.location.strip().lower())
        if key not in merged:
            merged[key] = f
        else:
            existing = merged[key]
            if f.found_by and f.found_by not in existing.confirmed_by:
                existing.confirmed_by.append(f.found_by)

    severity_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    return sorted(merged.values(), key=lambda f: severity_rank.get(f.severity, 9))
