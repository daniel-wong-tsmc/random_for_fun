import json, pathlib
from gpu_agent.assignment import load_assignment
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG, TAX = pathlib.Path("registry/indicators.json"), pathlib.Path("docs/taxonomy.json")

def _f(fid, indicatorId, pol_d, pol_s, mag, entity):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["models.frontier-closed"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity=entity,
        observedAt="2026-06", capturedAt="2026-06-25T00:00:00Z")

def test_new_category_validates_and_scores_without_code_change():
    a = load_assignment("fixtures/asg.models.frontier-closed.json")
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    assert validate_assignment(a, reg, tax) == []
    findings = [_f("x", "apiArr", 1, 0, 3, "openai"),
                _f("y", "releaseCadence", 1, 0, 2, "anthropic")]
    b = build_briefing(findings, reg, a.category)
    assert "momentum" in b.grouped and "competitiveStructure" in b.grouped
    dmi, smi = dmi_smi_contribution(findings, reg, a.category)
    assert dmi == 0.20 * 1 * 3 / 3 + 0.10 * 1 * 2 / 3   # 0.20 + 0.0667
    assert smi == 0.0
