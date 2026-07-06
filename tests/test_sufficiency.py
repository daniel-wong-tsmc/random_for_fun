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


# --- F71 (contract v1.4): anchor-forced-move exemption from the sufficiency gate ---

def test_anchor_forced_move_is_exempt_and_stamped():
    # Prior "Weak" is ILLEGAL under a +1.0 anchor, so the move to (anchor-legal) "Mixed" is
    # anchor-FORCED code-computed evidence, not a judgment re-rate -> exempt from sufficiency
    # even though the citation is under-sourced (1 publisher). Stamped for the trust footer.
    mem = _memory({"momentum": "Weak"})
    ans = _answer({"momentum": ("Mixed", ["s1"])})
    exemptions = {}
    violations = check_sufficiency([ans], mem, FBI, anchors={"momentum": 1.0},
                                   exemptions=exemptions)
    assert violations == []
    assert exemptions == {"momentum": "anchor-bounded on thin evidence"}


def test_genuine_rerate_same_thin_evidence_still_blocked():
    # Over-loosening guard: prior "Strong" is STILL anchor-legal at +1.0, so a move to "Very
    # strong" is a genuine judgment re-rate, not anchor-forced -> blocked exactly as before.
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["s1"])})
    exemptions = {}
    violations = check_sufficiency([ans], mem, FBI, anchors={"momentum": 1.0},
                                   exemptions=exemptions)
    assert len(violations) == 1 and "insufficient evidence" in violations[0]
    assert exemptions == {}


def test_exemption_requires_anchors_argument():
    # Without anchors (today's callers), behavior is byte-identical: no exemption path exists.
    mem = _memory({"momentum": "Weak"})
    ans = _answer({"momentum": ("Mixed", ["s1"])})
    assert len(check_sufficiency([ans], mem, FBI)) == 1


def test_exemption_only_when_new_rating_resolves_the_conflict():
    # The move must RESOLVE the anchor conflict: prior "Weak" illegal AND new "Very weak" still
    # illegal at +1.0 -> not exempt (the anchor gate owns the still-illegal rating separately).
    mem = _memory({"momentum": "Weak"})
    ans = _answer({"momentum": ("Very weak", ["s1"])})
    exemptions = {}
    violations = check_sufficiency([ans], mem, FBI, anchors={"momentum": 1.0},
                                   exemptions=exemptions)
    assert len(violations) == 1
    assert exemptions == {}
