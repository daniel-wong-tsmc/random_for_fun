from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Finding, Confidence, Impact, Evidence


def _f(evidence, level="high"):
    return Finding(
        id="doc-x-1", statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level=level, basis="b"), asOf="2026-07",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="NVDA", observedAt="2026-07-01",
        capturedAt="2026-07-04T00:00:00Z", evidence=evidence)


def _sec(url):
    # excerpt keyed to the URL so distinct URLs carry distinct bodies (genuine reporting);
    # the F72 near-dup collapse only merges byte-identical bodies (use _sec_body for that).
    return Evidence(source="s", url=url, date="2026-07-01", excerpt=f"body:{url}", tier="secondary")


def _sec_body(url, excerpt):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt=excerpt, tier="secondary")


# F72 (contract v1.4): one wire story mirrored across syndicator / near-dup domains.
_WIRE = ("Acme Corp announces expanded GPU capacity agreement with a hyperscale customer, "
         "effective Q3.")


def test_f2e_syndicated_wire_three_domains_fails_high_bar():
    # Three syndicator domains, one story -> registry collapse -> 1 distinct publisher < 3.
    f = _f([_sec_body("https://www.stocktitan.net/news/ACME/x.html", _WIRE),
            _sec_body("https://markets.financialcontent.com/stocks/news/read/ACME/y", _WIRE),
            _sec_body("https://finance.yahoo.com/news/acme-z.html", _WIRE)])
    errs = [e for e in check_finding(f) if "secondary-only" in e]
    assert "(1 distinct publishers < 3)" in errs[0]


def test_f2e_byte_identical_bodies_nonregistry_collapse_to_one():
    # Verbatim reprint on three UNKNOWN domains -> content-hash near-dup -> 1 distinct < 3.
    f = _f([_sec_body("https://alpha-news.example/a", _WIRE),
            _sec_body("https://beta-wire.example/b", _WIRE),
            _sec_body("https://gamma-feed.example/c", _WIRE)])
    errs = [e for e in check_finding(f) if "secondary-only" in e]
    assert "(1 distinct publishers < 3)" in errs[0]


def test_f2e_three_distinct_outlets_distinct_bodies_still_pass():
    # Regression: genuine reporting (different bodies, non-syndicator) still corroborates at 3.
    f = _f([_sec_body("https://reuters.com/a", "Reuters: capacity up."),
            _sec_body("https://digitimes.com/b", "DigiTimes: packaging tight."),
            _sec_body("https://tomshardware.com/c", "Toms: prices move.")])
    assert not [e for e in check_finding(f) if "secondary-only" in e]


def test_three_distinct_secondary_publishers_support_high():
    f = _f([_sec("https://reuters.com/a"), _sec("https://digitimes.com/b"),
            _sec("https://tomshardware.com/c")])
    assert not [e for e in check_finding(f) if "secondary-only" in e]


def test_two_distinct_publishers_still_rejected_with_count():
    f = _f([_sec("https://reuters.com/a"), _sec("https://digitimes.com/b")])
    errs = [e for e in check_finding(f) if "secondary-only" in e]
    assert errs == ["doc-x-1: secondary-only evidence cannot support high confidence "
                    "(2 distinct publishers < 3)"]


def test_syndication_same_netloc_collapses_to_one():
    f = _f([_sec("https://reuters.com/a"), _sec("https://www.reuters.com/b"),
            _sec("https://reuters.com/c")])
    errs = [e for e in check_finding(f) if "secondary-only" in e]
    assert "(1 distinct publishers < 3)" in errs[0]


def test_medium_confidence_never_touched():
    f = _f([_sec("https://reuters.com/a")], level="medium")
    assert not [e for e in check_finding(f) if "secondary-only" in e]


def test_primary_evidence_path_unchanged():
    prim = Evidence(source="sec.gov", url="https://sec.gov/x", date="2026-07-01",
                    excerpt="e", tier="primary")
    f = _f([prim])
    assert not [e for e in check_finding(f) if "secondary-only" in e]
