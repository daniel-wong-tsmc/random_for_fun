from __future__ import annotations
from pydantic import BaseModel
from gpu_agent.llm.client import LLMError, complete_with_retry

class ClaudeCodeClient:
    """Default backend (spec §10): drives Claude via the Claude Code subscription token
    (CLAUDE_CODE_OAUTH_TOKEN) through the Claude Agent SDK. The instruct-JSON + validate +
    retry loop is load-bearing here because this path lacks the raw API's strict
    output_config.format enforcement.

    BUILD-TIME VERIFICATION REQUIRED: confirm the claude_agent_sdk call surface against the
    installed package before finalizing `_raw_complete` (the import and call below are the
    documented single-shot query shape; adjust to the installed version if it differs).
    This method has NO unit coverage — the gated live smoke (Task 9) is its only test.
    """
    def __init__(self, **opts):
        self._opts = opts

    def _raw_complete(self, prompt: str, system: str, model: str) -> str:
        import asyncio
        from claude_agent_sdk import query, ClaudeAgentOptions  # lazy; verify names at build time
        async def _run() -> str:
            chunks: list[str] = []
            async for message in query(
                prompt=f"{system}\n\n{prompt}",
                options=ClaudeAgentOptions(model=model),
            ):
                text = getattr(message, "text", None)
                if text:
                    chunks.append(text)
            return "".join(chunks)
        out = asyncio.run(_run())
        if not out:
            raise LLMError("empty response from Claude Code backend")
        return out

    def complete_json(self, prompt: str, system: str, schema: type[BaseModel], model: str) -> BaseModel:
        return complete_with_retry(self._raw_complete, prompt, system, schema, model)
