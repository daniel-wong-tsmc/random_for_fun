"""Wave-2 Lane G robustness bundle: F41 (non-finite values, timestamp normalization,
wiki page id validation, crash-recoverable routing), F42 (config paths), F50 (run asOf
owns the scorecard label), F26-cli (de-GPU'd judge --category default)."""
from __future__ import annotations
import json
import pathlib
from gpu_agent.cli import main


PIPELINE_ARGS = [
    "--docs", "fixtures/raw",
    "--assignment", "fixtures/asg.chips.merchant-gpu.json",
    "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
    "--recorded-extract", "fixtures/recorded/extract-nvda.json",
    "--recorded-judge", "fixtures/recorded/judge-nvda.json",
]


# --- Task 1: F50 — the run's asOf owns the scorecard label ---------------------------

def test_pipeline_asof_matches_assignment_no_override_note(tmp_path, capsys):
    store = tmp_path / "store"
    rc = main(["pipeline", *PIPELINE_ARGS, "--as-of", "2026-06", "--out", str(store)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "F50" not in err
    written = list((store / "chips.merchant-gpu").glob("2026-06-v*.json"))
    assert written, "pipeline wrote no scorecard at the fixture's own asOf"


def test_pipeline_divergent_asof_overrides_assignment_and_notes(tmp_path, capsys):
    store = tmp_path / "store"
    rc = main(["pipeline", *PIPELINE_ARGS, "--as-of", "2026-07", "--out", str(store)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "note: assignment asOf 2026-06 overridden by run asOf 2026-07 (F50)" in err
    written = list((store / "chips.merchant-gpu").glob("2026-07-v*.json"))
    assert written, "scorecard was not labeled with the RUN asOf"
    stale = list((store / "chips.merchant-gpu").glob("2026-06-v*.json"))
    assert not stale, "scorecard was mislabeled with the stale fixture-assignment asOf"
    sc = json.loads(written[0].read_text("utf-8"))
    assert sc["asOf"] == "2026-07"
