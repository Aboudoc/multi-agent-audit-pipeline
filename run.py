#!/usr/bin/env python3
"""CLI entry point.

    python run.py examples/                      # audit every .sol under examples/
    python run.py examples/Vault.sol             # audit one file
    python run.py examples/ --dry-run            # no API call — just show the plan
    python run.py examples/Vault.sol --markdown > report.md   # plain Markdown report
    AUDIT_MODEL=claude-haiku-4-5 python run.py examples/      # force one model for all agents
"""

from __future__ import annotations

import argparse
import os
import sys

from pipeline import report
from pipeline.agents import AGENTS
from pipeline.codebase import load_codebase
from pipeline.orchestrator import audit


def main() -> int:
    ap = argparse.ArgumentParser(description="Tiny multi-agent Solidity audit pipeline")
    ap.add_argument("path", help="A .sol file or a directory of .sol files")
    ap.add_argument("--dry-run", action="store_true", help="Show the plan without calling the API")
    ap.add_argument("--sequential", action="store_true", help="Run agents one at a time, not in parallel")
    ap.add_argument("--markdown", action="store_true", help="Emit a plain Markdown report (good for files)")
    ap.add_argument("--model", default=None, help="Force ONE model for all agents (default: per-agent tiers)")
    args = ap.parse_args()

    override = args.model
    colors = report.agent_colors(AGENTS)
    file_desc = os.path.basename(os.path.normpath(args.path))

    if args.dry_run:
        report.print_plan(AGENTS, override, file_desc, colors)
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Set it, or try a free dry run:")
        print(f"  python run.py {args.path} --dry-run")
        return 1

    codebase = load_codebase(args.path)

    # Live scan log goes to stderr, so `--markdown > report.md` keeps a clean file.
    if not args.markdown:
        report.log_header(file_desc, AGENTS, override, colors)
    findings = audit(
        codebase,
        model_override=override,
        parallel=not args.sequential,
        on_done=None if args.markdown else (lambda a, fs: report.log_done(a, colors, len(fs))),
    )

    print(report.render_markdown(findings) if args.markdown else report.render(findings, colors))
    return 0


if __name__ == "__main__":
    sys.exit(main())
