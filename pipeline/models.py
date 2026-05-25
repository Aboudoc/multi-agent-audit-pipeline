"""Data shapes for findings. Pydantic gives us validation + a clean merge step."""

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["high", "medium", "low", "info"]


class Finding(BaseModel):
    title: str = Field(description="Short, specific title for the issue")
    severity: Severity = Field(description="high | medium | low | info")
    contract: str = Field(description="Contract where the issue lives")
    location: str = Field(description="Function name and/or a line hint")
    explanation: str = Field(description="Why it's exploitable / what goes wrong")
    recommendation: str = Field(description="How to fix it")
    # Set by the orchestrator after parsing — not asked of the model.
    found_by: str = ""
    confirmed_by: list[str] = Field(default_factory=list)


# JSON schema the model must fill. Kept hand-written (not generated) so it's easy
# to read and so `additionalProperties: false` is explicit — structured outputs
# require it. See README for how this maps to `output_config`.
FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["high", "medium", "low", "info"]},
                    "contract": {"type": "string"},
                    "location": {"type": "string"},
                    "explanation": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": [
                    "title",
                    "severity",
                    "contract",
                    "location",
                    "explanation",
                    "recommendation",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}
