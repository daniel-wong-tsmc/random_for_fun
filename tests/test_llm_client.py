import pytest
from pydantic import BaseModel
from gpu_agent.llm.client import LLMError, parse_and_validate, complete_with_retry

class _Foo(BaseModel):
    x: int

def test_parse_and_validate_ok():
    assert parse_and_validate('{"x": 5}', _Foo).x == 5

def test_parse_and_validate_raises_on_bad_json():
    with pytest.raises(Exception):
        parse_and_validate("not json", _Foo)

def test_retry_succeeds_after_one_bad_response():
    calls = []
    scripted = iter(["oops not json", '{"x": 7}'])
    def raw(prompt, system, model):
        calls.append(prompt)
        return next(scripted)
    out = complete_with_retry(raw, "extract", "sys", _Foo, "m", retries=2)
    assert out.x == 7
    assert len(calls) == 2
    assert "extract" in calls[1]  # corrective retry keeps the original prompt

def test_retry_exhausted_raises_llmerror():
    def raw(prompt, system, model):
        return "still not json"
    with pytest.raises(LLMError):
        complete_with_retry(raw, "p", "s", _Foo, "m", retries=2)
