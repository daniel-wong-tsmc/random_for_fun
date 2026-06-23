import pytest
from pydantic import BaseModel
from gpu_agent.llm.factory import make_client
from gpu_agent.llm.anthropic_api import AnthropicAPIClient
from gpu_agent.llm.claude_code import ClaudeCodeClient

class _Foo(BaseModel):
    x: int

def test_factory_selects_backends():
    assert isinstance(make_client("anthropic_api"), AnthropicAPIClient)
    assert isinstance(make_client("claude_code"), ClaudeCodeClient)
    with pytest.raises(ValueError):
        make_client("nope")

def test_backend_construction_does_not_require_sdk():
    # constructing must not import anthropic / claude_agent_sdk (lazy import on use)
    AnthropicAPIClient()
    ClaudeCodeClient()

def test_complete_json_runs_retry_loop_over_raw(monkeypatch):
    c = AnthropicAPIClient()
    scripted = iter(["bad", '{"x": 4}'])
    monkeypatch.setattr(c, "_raw_complete", lambda p, s, m: next(scripted))
    assert c.complete_json("p", "s", _Foo, "m").x == 4
