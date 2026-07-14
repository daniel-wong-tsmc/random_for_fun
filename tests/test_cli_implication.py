"""F65 Task 6 (acceptance 2/3/4): the `implication` CLI verb (emit -> recorded, one author)
and the report handler surfacing FOR TSMC from the stored artifact."""
from __future__ import annotations
import json
from pathlib import Path
from gpu_agent.cli import main
from gpu_agent.implication import ImplicationStore, ImplicationArtifact, ImplicationLine
from gpu_agent.report import load_scorecard

FIX = "fixtures/report/postb-scorecard.json"
SC = load_scorecard(Path(FIX))          # categoryId=chips.merchant-gpu, asOf=2026-06
AS_OF = SC.asOf
FID = SC.findings[0].id                  # doc-nvda-1


def test_emit_prompt_prints_bundle(tmp_path, capsys):
    rc = main(["implication", "--emit-prompt", "--scorecard", FIX, "--store", str(tmp_path),
               "--category", "chips.merchant-gpu", "--as-of", AS_OF])
    assert rc == 0
    bundle = json.loads(capsys.readouterr().out)
    assert set(bundle) == {"system", "schema", "user"}
    assert "decisionVariables" in bundle["user"]
    # registry-driven: a seeded variable label appears in the emitted prompt.
    assert "Advanced-packaging" in bundle["user"]


def test_recorded_gates_and_writes(tmp_path):
    answer = {"lines": [{"watchItem": "Advanced-packaging tightness caps the revenue ceiling.",
                         "dimensions": [], "thesisIds": [], "findingIds": [FID]}]}
    ap = tmp_path / "answer.json"
    ap.write_text(json.dumps(answer), "utf-8")
    rc = main(["implication", "--recorded", str(ap), "--scorecard", FIX, "--store", str(tmp_path),
               "--category", "chips.merchant-gpu", "--as-of", AS_OF])
    assert rc == 0
    art = ImplicationStore(tmp_path / "implications" / "chips.merchant-gpu").load(AS_OF)
    assert art.lines[0].findingIds == [FID]
    assert art.categoryId == "chips.merchant-gpu" and art.asOf == AS_OF


def test_recorded_gate_rejection_exits_1_no_write(tmp_path):
    answer = {"lines": [{"watchItem": "TSMC should build more capacity.", "findingIds": []}]}
    ap = tmp_path / "answer.json"
    ap.write_text(json.dumps(answer), "utf-8")
    rc = main(["implication", "--recorded", str(ap), "--scorecard", FIX, "--store", str(tmp_path),
               "--category", "chips.merchant-gpu", "--as-of", AS_OF])
    assert rc == 1
    assert not (tmp_path / "implications").exists()


def test_category_mismatch_exits_2(tmp_path):
    rc = main(["implication", "--emit-prompt", "--scorecard", FIX, "--store", str(tmp_path),
               "--category", "models.frontier-closed", "--as-of", AS_OF])
    assert rc == 2


def test_neither_flag_exits_2(tmp_path):
    rc = main(["implication", "--scorecard", FIX, "--store", str(tmp_path),
               "--category", "chips.merchant-gpu", "--as-of", AS_OF])
    assert rc == 2


def test_report_renders_for_tsmc_from_store(tmp_path, capsys):
    store = ImplicationStore(tmp_path / "implications" / "chips.merchant-gpu")
    store.write(ImplicationArtifact(categoryId=SC.categoryId, asOf=SC.asOf,
        lines=[ImplicationLine(watchItem="Pricing leverage holds this cycle.",
                               dimensions=["momentum"])]))
    rc = main(["report", "--scorecard", FIX, "--store", str(tmp_path), "--render-ts", "fixed"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FOR TSMC" in out
    assert "Pricing leverage holds this cycle." in out


def test_report_honest_empty_state_when_no_artifact(tmp_path, capsys):
    rc = main(["report", "--scorecard", FIX, "--store", str(tmp_path), "--render-ts", "fixed"])
    assert rc == 0
    assert "no implication recorded this cycle" in capsys.readouterr().out
