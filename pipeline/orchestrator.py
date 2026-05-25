"""Fan out to the agents, then merge and de-duplicate their findings."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .agents import AGENTS, Agent
from .llm import MODEL_OVERRIDE, run_agent
from .models import Finding


def audit(
    codebase: str,
    model_override: str | None = None,
    agents: list[Agent] = AGENTS,
    dry_run: bool = False,
    parallel: bool = True,
) -> list[Finding]:
    """Run every agent over the codebase and return merged, de-duplicated findings.

    Each agent uses its own model tier (agents.py) unless `model_override` (or the
    AUDIT_MODEL env var) forces one model for all of them.
    """
    override = model_override or MODEL_OVERRIDE

    if dry_run:
        print(f"DRY RUN — would run {len(agents)} agents:")
        for a in agents:
            print(f"  • {a.name} [{override or a.model}]: {a.focus.split('.')[0]}.")
        print(f"\nCodebase loaded: {len(codebase):,} chars.")
        print("Set ANTHROPIC_API_KEY and drop --dry-run to run for real.")
        return []

    raw: list[Finding] = []
    if parallel:
        # Fan out. (The first call warms the prompt cache; the rest read it.)
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            for findings in pool.map(lambda a: run_agent(a, codebase, override), agents):
                raw.extend(findings)
    else:
        for a in agents:
            raw.extend(run_agent(a, codebase, override))

    return _merge(raw)


def _merge(findings: list[Finding]) -> list[Finding]:
    """Collapse near-duplicate findings on the same spot; track multi-agent confirmation."""
    merged: dict[tuple[str, str], Finding] = {}
    for f in findings:
        key = (f.contract.strip().lower(), f.location.strip().lower())
        if key not in merged:
            merged[key] = f
        else:
            # Same spot flagged by another agent — record the confirmation.
            existing = merged[key]
            if f.found_by and f.found_by not in existing.confirmed_by:
                existing.confirmed_by.append(f.found_by)

    severity_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    return sorted(merged.values(), key=lambda f: severity_rank.get(f.severity, 9))
