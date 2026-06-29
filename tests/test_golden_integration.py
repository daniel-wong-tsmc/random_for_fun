import json, pathlib
from gpu_agent.cli import main

def test_cli_produces_golden_scorecard(tmp_path):
    rc = main(["run", "--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--fixtures", "fixtures/golden", "--out", str(tmp_path)])
    assert rc == 0
    written = sorted((tmp_path / "chips.merchant-gpu").glob("*.json"))[0]
    got = json.loads(written.read_text("utf-8"))
    golden = json.loads(pathlib.Path("fixtures/golden/scorecard.json").read_text("utf-8"))
    got.pop("provenance", None)
    assert got["demandSupply"] == golden["demandSupply"]
    assert {f["entity"] for f in got["findings"]} == {"NVDA", "AMD", "INTC"}
    assert set(got["dimensionRatings"].keys()) >= {"momentum", "competitiveStructure", "moat"}

def test_cli_run_populates_indices_on_golden(tmp_path):
    rc = main(["run", "--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--fixtures", "fixtures/golden", "--out", str(tmp_path)])
    assert rc == 0
    written = sorted((tmp_path / "chips.merchant-gpu").glob("*.json"))[0]
    got = json.loads(written.read_text("utf-8"))
    idx = got["indices"]
    assert idx is not None
    # golden findings are all lagging/coincident -> Momentum == blended demandSupply, Outlook all-zero
    assert idx["momentum"]["dmiContribution"] == got["demandSupply"]["dmiContribution"]
    assert idx["momentum"]["smiContribution"] == got["demandSupply"]["smiContribution"]
    assert idx["outlook"]["dmiContribution"] == 0.0 and idx["outlook"]["smiContribution"] == 0.0
    assert idx["divergence"]["state"] == "insufficient-coverage"
    assert idx["divergence"]["outlookFindingCount"] == 0
    # every golden finding is a contributing (scoring, non-overlay) momentum signal
    assert idx["divergence"]["momentumFindingCount"] == len(got["findings"])
