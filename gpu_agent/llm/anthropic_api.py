from __future__ import annotations
from pydantic import BaseModel
from gpu_agent.llm.client import LLMError, complete_with_retry

class AnthropicAPIClient:
    """Alternate backend: the `anthropic` SDK + ANTHROPIC_API_KEY (spec §10)."""
    def __init__(self, model_client=None):
        self._client = model_client  # injected for tests; lazily built otherwise

    def _ensure_client(self):
        if self._client is None:
            import anthropic  # lazy: only needed for live calls
            self._client = anthropic.Anthropic()
        return self._client

    def _raw_complete(self, prompt: str, system: str, model: str) -> str:
        resp = self._ensure_client().messages.create(
            model=model, max_tokens=16000, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.stop_reason == "refusal":
            raise LLMError("model refused the extraction request")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if text is None:
            raise LLMError("no text block in model response")
        return text

    def complete_json(self, prompt: str, system: str, schema: type[BaseModel], model: str) -> BaseModel:
        return complete_with_retry(self._raw_complete, prompt, system, schema, model)
