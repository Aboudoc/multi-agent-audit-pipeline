"""A tiny multi-agent Solidity audit pipeline.

An orchestrator fans an audit out across several focused agents (each hunts one
bug class), then merges and de-duplicates their findings. Built for teaching, not
for production — it's a loop, a few prompts, and a merge step.
"""

__version__ = "0.1.0"
