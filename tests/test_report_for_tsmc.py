"""F65 Task 5 (acceptance 4): the FOR TSMC brief section — pure projection of the stored
artifact, honest empty state, acronym-clean above the fold, appendix untouched, existing
callers byte-identical."""
from __future__ import annotations
from gpu_agent import reader
from gpu_agent.report import render_report, render_for_tsmc
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence
from gpu_agent.implication import ImplicationArtifact, ImplicationLine

REG = IndicatorRegistry.load("registry/indicators.json")


def _sc():
    return Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                     demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                     narrative="n", confidence=Confidence(level="medium", basis="b"))


def test_section_renders_from_artifact():
    art = ImplicationArtifact(categoryId="chips.merchant-gpu", asOf="2026-07-08",
        lines=[ImplicationLine(watchItem="Advanced-packaging tightness caps the revenue ceiling.",
                               dimensions=["bottleneck"], findingIds=["f-1"])])
    s = render_for_tsmc(art)
    assert "FOR TSMC" in s
    assert "Advanced-packaging tightness" in s
    assert reader.lint_acronyms(s) == []   # header ("FOR", "TSMC") + body pass the reader contract


def test_honest_empty_state():
    assert "no implication recorded this cycle" in render_for_tsmc(None)
    assert "no implication recorded this cycle" in render_for_tsmc(
        ImplicationArtifact(categoryId="c", asOf="a", lines=[]))


def test_render_report_omits_section_when_not_passed():
    # Existing callers (no implications arg) stay byte-identical and show no FOR TSMC section.
    a = render_report(_sc(), None, REG, render_ts="fixed")
    b = render_report(_sc(), None, REG, render_ts="fixed")
    assert a == b
    assert "FOR TSMC" not in a


def test_render_report_includes_section_when_passed_above_appendix():
    art = ImplicationArtifact(categoryId="chips.merchant-gpu", asOf="2026-07-08",
        lines=[ImplicationLine(watchItem="Pricing leverage holds as demand outruns supply.",
                               dimensions=["momentum"], findingIds=["f-1"])])
    out = render_report(_sc(), None, REG, render_ts="fixed", implications=art)
    assert "FOR TSMC" in out
    assert out.index("FOR TSMC") < out.index(reader.APPENDIX_DIVIDER)


def test_empty_artifact_passed_shows_empty_state_above_appendix():
    art = ImplicationArtifact(categoryId="chips.merchant-gpu", asOf="2026-07-08", lines=[])
    out = render_report(_sc(), None, REG, render_ts="fixed", implications=art)
    assert "no implication recorded this cycle" in out
    assert out.index("FOR TSMC") < out.index(reader.APPENDIX_DIVIDER)
