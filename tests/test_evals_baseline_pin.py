"""THE prompt regression gate (F6, charter Part 24). If this fails: a brain prompt changed.
Do NOT update baseline.json by hand — run the run-eval skill (dispatched brains + graders),
then `gpu-agent eval rebaseline`. Skips only until the initial baseline lands (F6 Task 10)."""
from __future__ import annotations
import pathlib
import pytest
from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
from gpu_agent.evals.harness import load_baseline
from gpu_agent.evals.prompt_hash import compute_prompt_hashes
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy

BASELINE = pathlib.Path("fixtures/evals/baseline.json")
HASH_INPUT = pathlib.Path("fixtures/evals/hash-input.json")
pytestmark = pytest.mark.skipif(load_baseline(BASELINE) is None,
                                reason="no eval baseline yet (F6 Task 10 live run pending)")

def test_prompt_hashes_match_baseline():
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    taxonomy = Taxonomy.load(TAXONOMY_PATH)
    current = compute_prompt_hashes(registry, taxonomy, HASH_INPUT)
    pinned = load_baseline(BASELINE)["promptHashes"]
    assert current == pinned, (
        "PROMPT BUNDLE CHANGED — this is the F6 regression gate, not a broken test. "
        "Run the run-eval skill (dispatch brains + graders), then "
        "'gpu-agent eval rebaseline' to accept. Never hand-edit baseline.json. "
        f"drifted: {sorted(k for k in current if current[k] != pinned.get(k))}")

def test_baseline_integrity():
    b = load_baseline(BASELINE)
    seams = {"extract", "judge", "thesis", "implication"}   # F65: implication joined at re-gate
    assert b["schemaVersion"] == 2
    assert set(b["promptHashes"]) == seams
    assert len(b["replicates"]) == 3
    for rep in b["replicates"]:
        assert set(rep["seamMeans"]) == seams
        assert rep["cases"], "replicate has no case scores"
    assert set(b["seamMeans"]) == set(b["epsilon"]) == seams
    assert all(e > 0 for e in b["epsilon"].values())
    assert b["caseMedians"], "baseline has no case medians"
    prov = b["provenance"]
    assert prov["asOf"] and prov["graderModel"]
    assert "forceReason" in prov and "humanReview" in prov
