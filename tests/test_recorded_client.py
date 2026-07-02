import pytest
from pydantic import BaseModel
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.llm.client import LLMError

class _Foo(BaseModel):
    x: int

def test_replays_single_response():
    c = RecordedClient(['{"x": 3}'])
    assert c.complete_json("p", "s", _Foo, "m").x == 3

def test_bad_answer_fails_loud_and_does_not_consume_next():
    """F11: a single call gets exactly one recorded answer. A validation failure re-serves
    the SAME bad answer to the retry loop (it never recovers), so the call fails loud and
    the next answer is left untouched for the next call — no cross-attribution."""
    c = RecordedClient(["bad", '{"x": 9}'])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", _Foo, "m")
    assert c.complete_json("p", "s", _Foo, "m").x == 9

def test_exhausted_recordings_raise():
    c = RecordedClient([])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", _Foo, "m")
