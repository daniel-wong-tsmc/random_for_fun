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
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.gathering.dedup import classify_findings, DEFAULT_DEDUP_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value, Evidence


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


# ── Task 3: F10 — corroboration merge + dispersion in a mixed batch ───────────


def _finding(fid, entity, indicatorId, number, capturedAt, evidence):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=Value(number=number, unit="usd"), evidence=evidence,
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-07", capturedAt=capturedAt)


def test_classify_mixed_batch_corroboration_dispersion_and_independent_key(tmp_path):
    """A batch with: (a) two agreeing NVDA/D2 findings that must merge evidence, and
    (b) an unrelated AMD/S10 singleton that must pass through untouched — the two keys
    do not interfere with each other."""
    store = WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))
    ev_a = Evidence(source="NVIDIA 10-Q", url="http://sec/nvda", date="2026-07-01",
                    excerpt="e", tier="primary")
    ev_b = Evidence(source="Analyst note", url="http://blog/nvda", date="2026-07-02",
                    excerpt="e", tier="secondary")
    ev_c = Evidence(source="AMD 10-Q", url="http://sec/amd", date="2026-07-01",
                    excerpt="e", tier="primary")
    findings = [
        _finding("f-nvda-a", "NVDA", "D2", 75.2, "2026-07-01", [ev_a]),
        _finding("f-nvda-b", "NVDA", "D2", 75.2, "2026-07-02", [ev_b]),   # agrees -> merge
        _finding("f-amd", "AMD", "S10", 5.0, "2026-07-01", [ev_c]),      # unrelated key
    ]
    res = classify_findings(findings, store, config=DEFAULT_DEDUP_CONFIG)

    assert {fc.findingId for fc in res.new} == {"f-nvda-b", "f-amd"}
    by_id = {f.id: f for f in res.outFindings}
    assert len(by_id) == 2
    assert len(by_id["f-nvda-b"].evidence) == 2   # merged corroborating evidence
    assert by_id["f-nvda-b"].dispersion is None
    assert len(by_id["f-amd"].evidence) == 1      # untouched singleton
    mate = next(fc for fc in res.duplicate if fc.findingId == "f-nvda-a")
    assert mate.detail.startswith("corroborates f-nvda-b")


# ── Task 4: F13d — find_prior day grain + loud unmatched-file notes via CLI ───


def test_cli_report_notes_unmatched_stray_file_in_store(tmp_path, capsys):
    """`report` auto-discovery must not silently skip a stray non-scorecard file in the
    category dir — it prints one stderr note per unmatched name."""
    fix = pathlib.Path("fixtures/report/legacy-current.json")
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v1.json").write_text(fix.read_text("utf-8"), "utf-8")
    (cat_dir / "2026-06-v2.json").write_text(fix.read_text("utf-8"), "utf-8")
    (cat_dir / "notes.json").write_text("{}", "utf-8")
    rc = main(["report", "--scorecard", str(cat_dir / "2026-06-v2.json"),
               "--store", str(tmp_path)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "gpu-agent report: note: ignoring non-scorecard file notes.json" in err


# ── Task 5: F22d — no silent drops in _pipeline; no silent unreadable prior ───


def test_pipeline_gate_dropped_findings_are_reported_not_silent(tmp_path, capsys):
    """A recorded-extract draft that fails the gate must be surfaced via DROPPED +
    a 'gate dropped N finding(s)' summary line, identical style to `_extract`. Craft the
    recorded answer against the CURRENT FindingDraft schema by round-tripping the
    committed extract-nvda.json fixture's single draft (never hand-write draft JSON —
    the schema changes in a parallel stream): keep one clean copy so the pipeline still
    has a valid finding to judge/score, and break a second copy's `why` field."""
    raw_answers = json.loads(pathlib.Path("fixtures/recorded/extract-nvda.json").read_text("utf-8"))
    answer_obj = json.loads(raw_answers[0])
    clean_draft = answer_obj["drafts"][0]
    broken_draft = json.loads(json.dumps(clean_draft))  # round-trip copy, never hand-written
    broken_draft["why"] = ""   # gated field: check_finding requires a non-empty `why`
    answer_obj["drafts"] = [clean_draft, broken_draft]
    rec = tmp_path / "rec-extract-broken.json"
    rec.write_text(json.dumps([json.dumps(answer_obj)]), "utf-8")

    store = tmp_path / "store"
    rc = main(["pipeline", "--docs", "fixtures/raw",
               "--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
               "--recorded-extract", str(rec),
               "--recorded-judge", "fixtures/recorded/judge-nvda.json", "--no-voice-lint",
               "--out", str(store)])
    err = capsys.readouterr().err
    assert "DROPPED doc-nvda-2" in err
    assert "gate dropped 1 finding(s)" in err
    assert rc == 0   # the one surviving finding (doc-nvda-1) still carries the pipeline through


def test_report_explicit_corrupt_prior_warns_not_silent(tmp_path, capsys):
    """--prior <corrupt file>: stderr must contain a 'could not load prior' warning
    (this branch already exists; guard against regression)."""
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("not valid json", "utf-8")
    rc = main(["report", "--scorecard", "fixtures/report/legacy-current.json",
               "--prior", str(corrupt)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "could not load prior" in err


def test_report_auto_discovered_corrupt_prior_warns_not_silent(tmp_path, capsys):
    """F22d: the auto-discovery branch must not silently swallow an unreadable prior —
    it prints a warning instead of the old bare `pass`."""
    fix = pathlib.Path("fixtures/report/legacy-current.json")
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v1.json").write_text("not valid json", "utf-8")   # corrupt prior candidate
    (cat_dir / "2026-06-v2.json").write_text(fix.read_text("utf-8"), "utf-8")
    rc = main(["report", "--scorecard", str(cat_dir / "2026-06-v2.json"),
               "--store", str(tmp_path)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "could not load prior" in err
