#!/usr/bin/env python3
"""CLI entry point.

    python run.py examples/              # audit every .sol under examples/
    python run.py examples/Vault.sol     # audit one file
    python run.py examples/ --dry-run    # no API call — just show the plan
    AUDIT_MODEL=claude-haiku-4-5 python run.py examples/   # cheaper model
"""

from __future__ import annotations

import argparse
import os
import sys

from pipeline.codebase import load_codebase
from pipeline.models import Finding
from pipeline.orchestrator import audit


def render(findings: list[Finding]) -> str:
    if not findings:
        return "\nNo findings. (Either the code is clean, or the agents need sharper prompts.)\n"
    lines = [f"\n# Audit report — {len(findings)} finding(s)\n"]
    for i, f in enumerate(findings, 1):
        who = f.found_by + (f" (confirmed by {', '.join(f.confirmed_by)})" if f.confirmed_by else "")
        lines += [
            f"## {i}. [{f.severity.upper()}] {f.title}",
            f"- **Where:** `{f.contract}` — {f.location}",
            f"- **Found by:** {who}",
            f"- **Why:** {f.explanation}",
            f"- **Fix:** {f.recommendation}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Tiny multi-agent Solidity audit pipeline")
    ap.add_argument("path", help="A .sol file or a directory of .sol files")
    ap.add_argument("--dry-run", action="store_true", help="Show the plan without calling the API")
    ap.add_argument("--sequential", action="store_true", help="Run agents one at a time, not in parallel")
    ap.add_argument("--model", default=None, help="Force ONE model for all agents (default: per-agent tiers)")
    args = ap.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Set it, or try a free dry run:")
        print(f"  python run.py {args.path} --dry-run")
        return 1

    codebase = load_codebase(args.path)
    findings = audit(
        codebase,
        model_override=args.model,
        dry_run=args.dry_run,
        parallel=not args.sequential,
    )
    if not args.dry_run:
        print(render(findings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
