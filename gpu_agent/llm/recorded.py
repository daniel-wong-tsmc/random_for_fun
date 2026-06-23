from __future__ import annotations
from collections import deque
from pydantic import BaseModel
from gpu_agent.llm.client import LLMError, complete_with_retry

class RecordedClient:
    """Replays canned LLM responses in FIFO order (one per attempt) — deterministic test seam."""
    def __init__(self, responses: list[str]):
        self._responses = deque(responses)

    def _raw_complete(self, prompt: str, system: str, model: str) -> str:
        if not self._responses:
            raise LLMError("no recorded response for this call")
        return self._responses.popleft()

    def complete_json(self, prompt: str, system: str,
                      schema: type[BaseModel], model: str) -> BaseModel:
        return complete_with_retry(self._raw_complete, prompt, system, schema, model)
