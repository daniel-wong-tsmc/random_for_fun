import pytest
from pydantic import BaseModel
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.llm.client import LLMError

class _Foo(BaseModel):
    x: int

def test_replays_single_response():
    c = RecordedClient(['{"x": 3}'])
    assert c.complete_json("p", "s", _Foo, "m").x == 3

def test_replays_bad_then_good_via_retry():
    c = RecordedClient(["bad", '{"x": 9}'])
    assert c.complete_json("p", "s", _Foo, "m").x == 9

def test_exhausted_recordings_raise():
    c = RecordedClient([])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", _Foo, "m")
