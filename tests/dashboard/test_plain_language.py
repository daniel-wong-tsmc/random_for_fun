from gpu_agent.dashboard.glossary import load_glossary
from gpu_agent.dashboard.plain_language import (
    load_plain_language, resolve_text, dimension_key, claim_key, finding_key,
    STATE_OF_MARKET_KEY,
)

G = load_glossary()
PMAP = load_plain_language("tests/dashboard/fixtures/plain-2026-07-06.json")

def test_key_helpers():
    assert STATE_OF_MARKET_KEY == "stateOfMarket"
    assert dimension_key("bottleneck") == "dimension.bottleneck.rationale"
    assert claim_key("export-control-exposure") == "claim.export-control-exposure.statement"
    assert finding_key("abc-1") == "finding.abc-1.statement"

def test_fresh_rewrite_is_used_when_original_matches():
    text, pending = resolve_text(STATE_OF_MARKET_KEY, "Binding constraint is HBM.", PMAP, G)
    assert pending is False
    assert "specialized memory" in text

def test_drift_falls_back_and_flags_pending():
    text, pending = resolve_text(STATE_OF_MARKET_KEY, "A different sentence about HBM now.", PMAP, G)
    assert pending is True
    assert "high-bandwidth memory" in text   # term-swap applied

def test_missing_key_falls_back():
    text, pending = resolve_text("finding.zzz.statement", "raw HBM text", {}, G)
    assert pending is True
    assert "high-bandwidth memory" in text
