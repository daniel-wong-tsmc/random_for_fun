from __future__ import annotations
from pydantic import BaseModel
from gpu_agent.llm.client import LLMError

class ClaudeCodeClient:
    """The session IS the brain (charter Part 38): live runs emit canonical prompts
    (--emit-prompt), a dispatched tool-less subagent answers, and --recorded replays the
    answer through the deterministic gate. There is no SDK/API path.
    """
    def __init__(self, **opts):
        self._opts = opts

    def complete_json(self, prompt: str, system: str, schema: type[BaseModel], model: str) -> BaseModel:
        raise LLMError(
            "the claude_code backend is session-driven: run '<cmd> --emit-prompt', answer via a "
            "dispatched subagent, then replay with --recorded (see .claude/skills/run-cycle)")
