from __future__ import annotations
from gpu_agent.llm.client import LLMClient

def make_client(backend: str = "claude_code", **opts) -> LLMClient:
    if backend == "claude_code":
        from gpu_agent.llm.claude_code import ClaudeCodeClient
        return ClaudeCodeClient(**opts)
    if backend == "anthropic_api":
        from gpu_agent.llm.anthropic_api import AnthropicAPIClient
        return AnthropicAPIClient(**opts)
    raise ValueError(f"unknown backend: {backend}")
