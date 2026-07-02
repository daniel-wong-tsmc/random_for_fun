from __future__ import annotations
from collections import deque
from pydantic import BaseModel
from gpu_agent.llm.client import LLMError, complete_with_retry

class RecordedClient:
    """Replays canned LLM responses — ONE per complete_json call. A validation failure
    re-serves the SAME answer to the retry loop, so a bad answer fails loud instead of
    silently consuming the next call's answer (F11: no cross-attribution between docs)."""
    def __init__(self, responses: list[str]):
        self._responses = deque(responses)

    @property
    def remaining(self) -> int:
        return len(self._responses)

    def complete_json(self, prompt: str, system: str,
                      schema: type[BaseModel], model: str) -> BaseModel:
        if not self._responses:
            raise LLMError("no recorded response for this call")
        answer = self._responses.popleft()
        return complete_with_retry(lambda *a: answer, prompt, system, schema, model)
