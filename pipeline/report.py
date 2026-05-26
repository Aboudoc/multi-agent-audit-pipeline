"""Presentation: live scan log + the rendered report. Pure ANSI, no dependencies.

Color is on when stdout is a TTY (and NO_COLOR is unset), or forced with FORCE_COLOR.
When piped, output degrades to clean plain text — and `--markdown` gives you a report
file you can paste anywhere.
"""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from collections import Counter

from .models import Finding

_USE_COLOR = bool(os.environ.get("FORCE_COLOR")) or (
    sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
)

# Distinct hues, assigned to agents in order. Add agents → they cycle through these.
_PALETTE = ["95", "96", "94", "92", "93", "91"]  # magenta cyan blue green yellow red
# Severity "badges": reversed-color blocks so HIGH actually jumps out of the page.
_BADGE = {"high": "1;97;41", "medium": "1;30;43", "low": "1;97;44", "info": "1;30;47"}


def _wrap(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s


def _bold(s: str) -> str:
    return _wrap("1", s)


def _dim(s: str) -> str:
    return _wrap("2", s)


def _badge(sev: str) -> str:
    label = f" {sev.upper()} "
    return _wrap(_BADGE.get(sev, "7"), label) if _USE_COLOR else f"[{sev.upper()}]"


def _short_model(model: str) -> str:
    for tier in ("opus", "sonnet", "haiku"):
        if tier in model:
            return tier
    return model


def _width() -> int:
    return min(shutil.get_terminal_size((90, 24)).columns, 90)


def agent_colors(agents) -> dict:
    """Map each agent name to a stable colorizer (used in the log AND the report)."""
    out = {}
    for i, a in enumerate(agents):
        code = _PALETTE[i % len(_PALETTE)]
        out[a.name] = (lambda c: lambda s: _wrap(c, s))(code)
    return out


# ── live scan log (stderr, so piping stdout stays clean) ───────────────────────

def log_header(file_desc: str, agents, override, colors) -> None:
    print(f"\n{_bold('multi-agent-audit-pipeline')}  scanning {file_desc}\n", file=sys.stderr)
    for a in agents:
        model = _short_model(override or a.model)
        dot = colors[a.name]("●")
        print(f"  {dot} {colors[a.name](f'{a.name:<20}')} {_dim(f'[{model}]  scanning…')}", file=sys.stderr)
    print(file=sys.stderr)


def log_done(agent, colors, n: int) -> None:
    badge = f"{n} finding" + ("" if n == 1 else "s")
    tick = colors[agent.name]("✓")
    note = badge if n else _dim("clean")
    print(f"  {tick} {colors[agent.name](f'{agent.name:<20}')} {note}", file=sys.stderr)


def print_plan(agents, override, file_desc: str, colors) -> None:
    print(f"\n{_bold('DRY RUN')} — would scan {file_desc} with {len(agents)} agents:\n")
    for a in agents:
        model = _short_model(override or a.model)
        focus = a.focus.split(".")[0]
        print(f"  {colors[a.name]('●')} {colors[a.name](f'{a.name:<20}')} {_dim(f'[{model}]')}  {focus}.")
    print(f"\nSet ANTHROPIC_API_KEY and drop --dry-run to run for real.\n")


# ── the report ─────────────────────────────────────────────────────────────────

def render(findings: list[Finding], colors) -> str:
    if not findings:
        return f"\n  {_dim('No findings. Clean — or the agents need sharper prompts.')}\n"

    w = _width()
    counts = Counter(f.severity for f in findings)
    tally = "  ".join(
        f"{_badge(s)} {counts[s]}" for s in ("high", "medium", "low", "info") if counts[s]
    )
    n = len(findings)

    out = [
        "",
        _bold("  AUDIT REPORT"),
        f"  {n} finding{'' if n == 1 else 's'}   {tally}",
        "  " + _dim("━" * (w - 2)),
    ]
    for i, f in enumerate(findings, 1):
        who = colors.get(f.found_by, lambda s: s)(f.found_by)
        if f.confirmed_by:
            who += _dim(" +" + ", ".join(f.confirmed_by))
        out.append("")
        out.append(f"  {_bold(f'{i}.')} {_badge(f.severity)}  {_bold(f.title)}")
        out.append(f"     {f.contract} · {f.location}   {_dim('—')} {who}")
        for label, text in (("why", f.explanation), ("fix", f.recommendation)):
            body = textwrap.fill(text, width=w - 9).split("\n")
            out.append(f"     {_dim(label)}  {body[0]}")
            out.extend("          " + ln for ln in body[1:])
    out.append("")
    return "\n".join(out)


def render_markdown(findings: list[Finding]) -> str:
    """Plain Markdown — for `python run.py … --markdown > report.md`."""
    if not findings:
        return "\nNo findings.\n"
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
