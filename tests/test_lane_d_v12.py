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


# ── Task 2: F12 — L1 dedup records only after snapshots are durable ───────────


def test_ingest_records_only_after_docs_and_log_are_written(tmp_path, monkeypatch):
    """F12: crash-safety — record_documents must be called only after every doc file
    and gather-log.json are durably on disk, so a crash before that point loses
    nothing forever (the same docs get re-ingested next run instead of vanishing)."""
    from gpu_agent import cli as cli_module

    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([{"url": "http://x/a", "content": "c", "source": "s",
                                   "date": "2026-07", "entity": "NVDA"}]), "utf-8")
    out = tmp_path / "out"
    store = tmp_path / "store"

    calls = []
    real_record = cli_module.record_documents

    def spy(docs, index, *, as_of):
        calls.append(True)
        # by the time recording happens, every doc file AND gather-log.json must exist
        assert (out / f"{docs[0].id}.json").exists()
        assert (out / "gather-log.json").exists()
        return real_record(docs, index, as_of=as_of)

    monkeypatch.setattr(cli_module, "record_documents", spy)
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out),
               "--primary-sources", "sec.gov", "--dedup-store", str(store), "--as-of", "2026-07"])
    assert rc == 0
    assert calls  # record_documents was actually invoked
