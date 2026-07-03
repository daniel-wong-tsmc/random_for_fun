"""F53 — price rows must carry the registry's canonical unit for their indicatorId.

Born from the 2026-07-02/03 live cycles: 07-02 labeled Lambda rental rows D6/USD_per_gpu_hr,
07-03 labeled the same rows gpuSpotPrice/USD/GPU-hr — both registered, so nothing failed,
and the price track (keyed on indicatorId+publisher+unit) matched 0 series; PMI rendered
dead. The extractor seam now rejects a measured price-side draft whose value.unit differs
from the registered unit — catching BOTH the mislabel (a rental row tagged gpuSpotPrice
carries the wrong canonical unit) and free-text unit drift. gate.py stays frozen.
"""
import json

from gpu_agent.extraction.extractor import extract_findings
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.schema.raw_document import RawDocument

DOC = RawDocument(
    id="lambda-ai-845323fc-2026-07-03", source="Lambda (lambda.ai)",
    url="https://lambda.ai/service/gpu-cloud", date="2026-07-03",
    tier="secondary", entity="NVDA",
    content="NVIDIA B200 SXM6: 8x configuration $6.69/hr")


def _draft(indicator_id="D6", unit="USD_per_gpu_hr", **overrides):
    d = {
        "statement": "Lambda lists B200 rental at $6.69/hr per GPU.",
        "kind": "measured",
        "value": {"number": 6.69, "unit": unit},
        "trend": "unknown",
        "why": "Current rental level for the price overlay.",
        "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed",
                   "mechanism": "Price level display overlay."},
        "evidence": [{"source": "Lambda (lambda.ai)",
                      "url": "https://lambda.ai/service/gpu-cloud",
                      "date": "2026-07-03",
                      "excerpt": "NVIDIA B200 SXM6: 8x configuration $6.69/hr"}],
        "reasoning": None,
        "confidence": {"level": "medium", "basis": "Vendor price page (secondary)."},
        "dispersion": None,
        "indicatorId": indicator_id,
        "polarityDemand": 0, "polaritySupply": 0,
        "magnitude": 1, "entity": "NVDA", "observedAt": "2026-07-03",
    }
    d.update(overrides)
    return d


def _outcome(draft):
    client = RecordedClient([json.dumps({"drafts": [draft]})])
    return extract_findings(DOC, client, as_of="2026-07-03",
                            captured_at="2026-07-03T00:00:00Z",
                            extraction_model="test", model="test")


def test_canonical_unit_passes():
    out = _outcome(_draft())
    assert [f.id for f in out.findings] == ["lambda-ai-845323fc-2026-07-03-1"]
    assert out.dropped == []


def test_unit_drift_rejected_loud():
    out = _outcome(_draft(unit="USD/GPU-hr"))   # the literal 07-03 drift
    assert out.findings == []
    assert len(out.dropped) == 1
    assert ("price unit 'USD/GPU-hr' != registered unit 'USD_per_gpu_hr' for D6"
            in out.dropped[0].violations[0])


def test_mislabeled_rental_as_hardware_spot_rejected_loud():
    # a rental row (USD_per_gpu_hr) tagged gpuSpotPrice: canonical unit there is USD_per_gpu
    out = _outcome(_draft(indicator_id="gpuSpotPrice"))
    assert out.findings == []
    assert "!= registered unit 'USD_per_gpu' for gpuSpotPrice" in out.dropped[0].violations[0]


def test_price_row_without_value_is_untouched_by_the_unit_check():
    out = _outcome(_draft(kind="observed", value=None))
    assert out.dropped == []
    assert len(out.findings) == 1


def test_non_price_rows_unaffected():
    # D2 is side=demand: free-text unit is NOT checked here (F53 scope: price rows only)
    d = _draft(indicator_id="D2", unit="USD billions",
               polarityDemand=1, trend="rising",
               statement="DC revenue $6.69B.",
               why="Momentum read.")
    out = _outcome(d)
    assert out.dropped == []
    assert len(out.findings) == 1
