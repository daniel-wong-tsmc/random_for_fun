import pytest
from pydantic import BaseModel
from gpu_agent.llm.factory import make_client
from gpu_agent.llm.anthropic_api import AnthropicAPIClient
from gpu_agent.llm.claude_code import ClaudeCodeClient
from gpu_agent.llm.client import LLMError

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

# ── F40: ClaudeCodeClient is an honest signpost — there is no SDK/API path ──

def test_claude_code_complete_json_raises_llmerror_not_sdk_error():
    c = ClaudeCodeClient()
    with pytest.raises(LLMError) as exc_info:
        c.complete_json("p", "s", _Foo, "m")
    msg = str(exc_info.value)
    assert "--emit-prompt" in msg
    assert "--recorded" in msg

def test_claude_code_complete_json_raises_immediately_no_raw_complete_sdk_path():
    # The class must no longer expose an SDK-driving _raw_complete: calling
    # complete_json must not attempt to import claude_agent_sdk at all.
    c = ClaudeCodeClient(model="whatever")
    with pytest.raises(LLMError):
        c.complete_json("prompt", "system", _Foo, "model")
