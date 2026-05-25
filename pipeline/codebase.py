"""Load a Solidity codebase into one annotated string the agents can read."""

from pathlib import Path


def load_codebase(path: str) -> str:
    """Concatenate every .sol file under `path` (or a single file) into one blob.

    Each file is prefixed with a header so the model can cite file + line.
    For real audits you'd add scoping (skip tests/mocks/node_modules); kept
    minimal here on purpose.
    """
    p = Path(path)
    files = sorted(p.rglob("*.sol")) if p.is_dir() else [p]
    if not files:
        raise SystemExit(f"No .sol files found at {path!r}")

    blocks = []
    for f in files:
        blocks.append(f"// ===== FILE: {f} =====\n{f.read_text()}")
    return "\n\n".join(blocks)
