"""The agents. Each one hunts a single, well-known bug class.

Keeping each agent to ONE job is the whole idea: a focused prompt beats a
kitchen-sink "find all bugs" prompt, and the outputs are easy to merge. Add your
own agent by appending an `Agent(...)` to `AGENTS` — that's the extension point.

Each agent also picks a model that matches the *difficulty* of its job. Pattern
scans are cheap and fine on a small model; cross-function reasoning wants a bigger
one. Don't pay Opus prices for a grep.
"""

from dataclasses import dataclass

# Match the model to the task. Override globally with --model / AUDIT_MODEL.
HARD = "claude-opus-4-7"    # multi-step / cross-function reasoning
MIDDLE = "claude-sonnet-4-6"  # moderate reasoning
SIMPLE = "claude-haiku-4-5"   # mechanical pattern scans


@dataclass(frozen=True)
class Agent:
    name: str
    focus: str  # the user-message prompt; the codebase is shared via the system prompt
    model: str  # the tier that fits this agent's job


AGENTS: list[Agent] = [
    Agent(
        name="reentrancy",
        model=HARD,  # needs control-flow reasoning across calls and state writes
        focus=(
            "Hunt ONLY for reentrancy. Look for external calls (`.call`, `.transfer`, "
            "token callbacks, ERC777/ERC721 hooks) that happen before state is updated — "
            "i.e. violations of checks-effects-interactions — and for missing reentrancy "
            "guards on functions that move value. Ignore every other bug class. "
            "If there is no reentrancy, return an empty list."
        ),
    ),
    Agent(
        name="access-control",
        model=MIDDLE,  # moderate: map functions to the checks they should have
        focus=(
            "Hunt ONLY for access-control issues. Look for state-changing or value-moving "
            "functions that lack an owner/role check, missing or wrong modifiers, "
            "initializers that can be front-run or called twice, and privileged setters that "
            "anyone can call. Ignore every other bug class. If there is none, return an empty list."
        ),
    ),
    Agent(
        name="cross-function-auth",
        model=HARD,  # cross-function reasoning: who is acted on vs who is checked
        focus=(
            "Hunt ONLY for cross-function authorization gaps: a function that acts on a "
            "recipient/target argument (mints, credits, transfers, sets a balance/debt for `to`) "
            "but validates permission or solvency on msg.sender instead — state applied to A "
            "while checked against B. Ignore every other bug class. If there is none, return an empty list."
        ),
    ),
    Agent(
        name="integer-overflow",
        model=SIMPLE,  # mostly a pattern scan — a small model is plenty
        focus=(
            "Hunt ONLY for unsafe arithmetic: overflow/underflow in `unchecked` blocks, "
            "narrowing casts that truncate, pre-0.8 math without SafeMath, division before "
            "multiplication, and rounding that favors the wrong party. Note: Solidity >=0.8 "
            "reverts on overflow by default, so plain `+`/`-` outside `unchecked` is NOT a "
            "finding. Ignore every other bug class. If there is none, return an empty list."
        ),
    ),
]
