"""F55 — emitted prompts carry the id vocabularies the gates enforce.

Born from the 2026-07-03 and 2026-07 live cycles: both coordinating sessions had to hand the
brains the valid taxonomy category ids (extraction impact.targets) and the judge citation
groups out-of-band, and both got them wrong on the first try, costing a re-dispatch wave each.
The emit paths now bake the vocabularies into the canonical prompts; the default (no-arg)
prompt paths stay byte-identical, same additive pattern as F26 personas and F4 memory_text.
"""
import json
import subprocess
import sys

from gpu_agent.extraction import prompt as extraction_prompt
from gpu_agent.judgment import prompt as judgment_prompt
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Finding, Confidence, Impact
from gpu_agent.schema.scorecard import DIMENSIONS
from gpu_agent.thesis import THESIS_SYSTEM


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _f() -> Finding:
    return Finding(
        id="doc-nvda-1", statement="DC growth flattening", kind="observed", trend="flat",
        why="w", impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="high", basis="b"), asOf="2026-06", indicatorId="D2",
        side="demand", polarityDemand=1, polaritySupply=0, magnitude=2, entity="NVDA",
        observedAt="2026-06", capturedAt="2026-06-12T00:00:00Z")


# --- extraction: valid impact.targets ids ---

def test_extract_system_byte_identical_without_targets():
    assert extraction_prompt.build_system() == extraction_prompt.SYSTEM
    assert extraction_prompt.build_system(valid_targets=None) == extraction_prompt.SYSTEM


def test_extract_system_lists_valid_targets_when_given():
    s = extraction_prompt.build_system(valid_targets=["chips.merchant-gpu", "chips.hbm-memory"])
    assert "Valid impact.targets category ids" in s
    assert "chips.merchant-gpu, chips.hbm-memory" in s
    # the vocabulary block extends the canonical system, it does not rewrite it
    assert s.startswith(extraction_prompt.SYSTEM)


def test_extract_emit_prompt_carries_real_taxonomy_ids():
    out = _run("extract", "--emit-prompt", "--docs", "fixtures/raw", "--as-of", "2026-06")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "Valid impact.targets category ids" in bundle["system"]
    # real, layer-prefixed ids from docs/taxonomy.json — the exact vocabulary the gate enforces
    assert "chips.merchant-gpu" in bundle["system"]
    assert "chips.hyperscaler-asic" in bundle["system"]


# --- judgment: citation groups + the six dimension names ---

def test_judge_user_prompt_byte_identical_without_groups():
    reg = IndicatorRegistry.load("registry/indicators.json")
    briefing = build_briefing([_f()], reg, "chips.merchant-gpu")
    assert judgment_prompt.build_user_prompt(briefing) == \
        judgment_prompt.build_user_prompt(briefing, include_groups=False)
    assert "<citationGroups>" not in judgment_prompt.build_user_prompt(briefing)


def test_judge_user_prompt_groups_block_when_requested():
    reg = IndicatorRegistry.load("registry/indicators.json")
    briefing = build_briefing([_f()], reg, "chips.merchant-gpu")
    prompt = judgment_prompt.build_user_prompt(briefing, include_groups=True)
    assert "<citationGroups>" in prompt and "</citationGroups>" in prompt
    assert "momentum: doc-nvda-1" in prompt          # D2 groups under momentum
    for dim in DIMENSIONS:                            # the six real names, spelled out
        assert dim in prompt
    assert "OMIT any dimension not listed" in prompt


def test_judge_groups_compose_with_memory():
    reg = IndicatorRegistry.load("registry/indicators.json")
    briefing = build_briefing([_f()], reg, "chips.merchant-gpu")
    prompt = judgment_prompt.build_user_prompt(briefing, memory_text="X", include_groups=True)
    assert prompt.index("<memory>") < prompt.index("<briefing>") < prompt.index("<citationGroups>")


def test_judge_emit_prompt_carries_citation_groups(tmp_path):
    findings = tmp_path / "findings.json"
    out = _run("extract", "--recorded", "fixtures/recorded/extract-nvda.json",
               "--docs", "fixtures/raw", "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--out", str(findings))
    assert out.returncode == 0, out.stderr
    out = _run("judge", "--emit-prompt", "--findings", str(findings),
               "--category", "chips.merchant-gpu")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "<citationGroups>" in bundle["user"]
    assert "momentum:" in bundle["user"]


# --- thesis: the observable-trigger heuristic is stated, not discovered by rejection ---

def test_thesis_system_states_the_observable_heuristic():
    assert "registered indicator id" in THESIS_SYSTEM
    for word in ("quarter", "qtr", "month", "week", "cycle"):
        assert word in THESIS_SYSTEM
    assert "digit" in THESIS_SYSTEM


# --- extraction: price-indicator vocabulary (F53) ---

def test_extract_system_byte_identical_without_price_indicators():
    assert extraction_prompt.build_system(price_indicators=None) == extraction_prompt.SYSTEM


def test_extract_system_lists_price_vocabulary_when_given():
    s = extraction_prompt.build_system(price_indicators=[
        {"id": "D6", "label": "GPU rental price", "unit": "USD_per_gpu_hr",
         "comparability": ""},
        {"id": "gpuSpotPrice", "label": "Merchant-GPU hardware spot/resale price",
         "unit": "USD_per_gpu", "comparability": "secondary-market hardware price"},
    ])
    assert "Price-level rows (side=price) use EXACTLY one of these indicator ids" in s
    assert "D6 — GPU rental price, unit USD_per_gpu_hr" in s
    assert ("gpuSpotPrice — Merchant-GPU hardware spot/resale price, unit USD_per_gpu "
            "(secondary-market hardware price)") in s
    assert s.startswith(extraction_prompt.SYSTEM)   # extends, never rewrites


def test_extract_emit_prompt_carries_price_vocabulary_from_registry():
    out = _run("extract", "--emit-prompt", "--docs", "fixtures/raw", "--as-of", "2026-06")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "D6 — GPU rental price, unit USD_per_gpu_hr" in bundle["system"]
    assert "gpuSpotPrice — Merchant-GPU hardware spot/resale price, unit USD_per_gpu" \
        in bundle["system"]
    # composes with F55: targets vocabulary still present
    assert "Valid impact.targets category ids" in bundle["system"]
