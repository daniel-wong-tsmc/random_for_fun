"""Lane D — gather/dedup/CLI robustness (F10, F11, F12, F13-D, F22-D).

New coverage that doesn't fit the existing per-module test files. RecordedClient
tests use a TINY schema defined locally (RecordedClient is schema-agnostic) —
never an ExtractionResult-shaped answer (the draft schema changes in a parallel
stream). Any extraction-draft JSON here is round-tripped from the committed
fixtures/recorded/extract-nvda.json fixture, never hand-written.
"""
import json
import pathlib
import pytest
from pydantic import BaseModel

from gpu_agent.cli import main
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.llm.client import LLMError


class Tiny(BaseModel):
    x: int


# ── Task 1: F11 — one recorded answer per call, no cross-attribution ──────────


def test_invalid_answer_fails_loud_without_consuming_next():
    c = RecordedClient(['{"x": "not-an-int"}', '{"x": 2}'])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", Tiny, "m")       # burns ONLY answer 1
    assert c.remaining == 1
    assert c.complete_json("p", "s", Tiny, "m").x == 2   # answer 2 still paired


def test_one_answer_per_call():
    c = RecordedClient(['{"x": 1}', '{"x": 2}'])
    assert c.complete_json("p", "s", Tiny, "m").x == 1
    assert c.complete_json("p", "s", Tiny, "m").x == 2


def test_exhausted_fails_loud():
    c = RecordedClient([])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", Tiny, "m")


def test_cli_extract_recorded_count_mismatch_exits_2(tmp_path, capsys):
    # fixtures/raw has exactly 1 doc; feed it 3 recorded answers -> hard fail.
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps(["a", "b", "c"]), "utf-8")
    rc = main(["extract", "--docs", "fixtures/raw", "--as-of", "2026-06",
               "--recorded", str(rec)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "recorded answers (3) != documents (1)" in err
