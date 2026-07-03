# tests/test_evals_hash.py
from __future__ import annotations
import pathlib
from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
from gpu_agent.evals.emit import emit_brain_bundle, load_hash_input
from gpu_agent.evals.prompt_hash import compute_prompt_hashes
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy

HASH_INPUT = pathlib.Path("fixtures/evals/hash-input.json")

def _reg():
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    taxonomy = Taxonomy.load(TAXONOMY_PATH)
    return registry, taxonomy

def test_emit_bundles_have_prompt_parts():
    registry, taxonomy = _reg()
    inputs = load_hash_input(HASH_INPUT)
    for seam in ("extract", "judge", "thesis"):
        bundle = emit_brain_bundle(seam, inputs[seam], registry, taxonomy)
        assert set(bundle) == {"system", "schema", "user"}, seam
        assert isinstance(bundle["system"], str) and bundle["system"]
        assert isinstance(bundle["schema"], dict)
        assert isinstance(bundle["user"], str) and bundle["user"]

def test_hashes_deterministic_and_per_seam():
    registry, taxonomy = _reg()
    h1 = compute_prompt_hashes(registry, taxonomy, HASH_INPUT)
    h2 = compute_prompt_hashes(registry, taxonomy, HASH_INPUT)
    assert h1 == h2
    assert set(h1) == {"extract", "judge", "thesis"}
    assert len(set(h1.values())) == 3          # seams differ
    assert all(len(v) == 64 for v in h1.values())

def test_judge_user_prompt_carries_citation_groups():
    # F55 include_groups=True is part of the canonical judge prompt; pin that eval emits it
    registry, taxonomy = _reg()
    inputs = load_hash_input(HASH_INPUT)
    bundle = emit_brain_bundle("judge", inputs["judge"], registry, taxonomy)
    assert "citationGroups" in bundle["user"]
