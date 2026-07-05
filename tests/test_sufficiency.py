import json
from types import SimpleNamespace
from gpu_agent.schema.finding import Finding, Confidence, Impact, Evidence
from gpu_agent.sufficiency import check_sufficiency


def _ev(url, tier="secondary"):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt="e", tier=tier)


def _finding(fid, evidence):
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="NVDA", observedAt="2026-07-01",
        capturedAt="2026-07-04T00:00:00Z", evidence=evidence)


def _memory(ratings, bottleneck="bottleneck"):
    return SimpleNamespace(
        priorRatings={d: {"rating": r, "direction": "steady", "confidence": "medium"}
                      for d, r in ratings.items()},
        priorCategoryStatus={"bottleneck": bottleneck})


def _answer(dimensions, bottleneck="bottleneck"):
    return json.dumps({
        "dimensions": {d: {"rating": r, "direction": "steady", "findingIds": ids,
                           "rationale": "x"} for d, (r, ids) in dimensions.items()},
        "categoryStatus": {"rating": "Strong", "direction": "steady",
                           "bottleneck": bottleneck, "reason": "x"},
        "narrative": "One. Two. Three."})


FBI = {
    "prim": _finding("prim", [_ev("https://sec.gov/x", tier="primary")]),
    "s1": _finding("s1", [_ev("https://reuters.com/a")]),
    "s2": _finding("s2", [_ev("https://digitimes.com/b")]),
    "s3": _finding("s3", [_ev("https://tomshardware.com/c")]),
}


def test_no_memory_is_inert():
    ans = _answer({"momentum": ("Very strong", ["s1"])})
    assert check_sufficiency([ans], None, FBI) == []


def test_unchanged_rating_never_checked():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Strong", [])})       # unchanged, zero citations: fine
    assert check_sufficiency([ans], mem, FBI) == []


def test_primary_backed_change_passes():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["prim"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_three_publisher_change_passes():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["s1", "s2", "s3"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_two_publisher_change_fails_with_exact_line():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["s1", "s2"])})
    assert check_sufficiency([ans], mem, FBI) == [
        "sample 1: momentum: rating changed Strong->Very strong with insufficient "
        "evidence (no primary; 2 distinct publishers < 3)"]


def test_dimension_without_prior_is_exempt():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Strong", []), "moat": ("Weak", ["s1"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_bottleneck_change_checks_new_dimension():
    mem = _memory({"momentum": "Strong", "moat": "Mixed"}, bottleneck="momentum")
    ans = _answer({"momentum": ("Strong", []), "moat": ("Mixed", ["s1", "s2"])},
                  bottleneck="moat")
    assert check_sufficiency([ans], mem, FBI) == [
        "sample 1: categoryStatus.bottleneck: changed momentum->moat with insufficient "
        "evidence (no primary; 2 distinct publishers < 3)"]


def test_multi_sample_prefixes():
    mem = _memory({"momentum": "Strong"})
    good = _answer({"momentum": ("Strong", [])})
    bad = _answer({"momentum": ("Very strong", ["s1"])})
    violations = check_sufficiency([good, bad], mem, FBI)
    assert len(violations) == 1 and violations[0].startswith("sample 2: ")
