# tests/test_publisher.py
from types import SimpleNamespace
from gpu_agent.publisher import publisher_key, collapsed_publisher


def _e(url="", source="", excerpt="e"):
    return SimpleNamespace(url=url, source=source, excerpt=excerpt)


def test_netloc_lowercased_www_stripped():
    assert publisher_key(_e(url="https://www.Reuters.com/article/x")) == "reuters.com"


def test_distinct_paths_same_netloc_collapse():
    a = publisher_key(_e(url="https://digitimes.com/a"))
    b = publisher_key(_e(url="https://digitimes.com/b"))
    assert a == b == "digitimes.com"


def test_source_fallback_when_no_netloc():
    assert publisher_key(_e(url="not-a-url", source="  Dell'Oro Group ")) == "dell'oro group"


def test_wiki_lifecycle_reexport_is_same_object():
    from gpu_agent.wiki import lifecycle
    assert lifecycle._publisher_key is publisher_key


# --- F72 (contract v1.4): syndication-resistant collapsed publisher identity ---

# The three archetypal PR-syndication / aggregator endpoints the backlog names
# (docs/fix-backlog.md:572-573; f72-adversarial-fixture.md §2).
_STOCKTITAN = "https://www.stocktitan.net/news/ACME/acme-corp-announces-abc123.html"
_FINCONTENT = "https://markets.financialcontent.com/stocks/news/read/ACME/acme-corp-announces"
_YAHOO = "https://finance.yahoo.com/news/acme-corp-announces-capacity-deal.html"


def test_collapsed_publisher_non_syndicator_unchanged():
    # A genuine outlet is returned exactly as publisher_key would key it.
    e = _e(url="https://www.Reuters.com/article/x")
    assert collapsed_publisher(e) == publisher_key(e) == "reuters.com"


def test_syndicator_registry_collapses_three_domains_to_one():
    # One wire story mirrored on three syndicator domains -> ONE originating-publisher
    # identity (registry lookup alone, no near-dup content collapse needed here).
    a = collapsed_publisher(_e(url=_STOCKTITAN))
    b = collapsed_publisher(_e(url=_FINCONTENT))
    c = collapsed_publisher(_e(url=_YAHOO))
    assert a == b == c
    assert len({a, b, c}) == 1


def test_three_genuine_outlets_stay_distinct():
    # Regression guard: three real, non-syndicator outlets remain three identities.
    ids = {collapsed_publisher(_e(url=u)) for u in (
        "https://reuters.com/a", "https://digitimes.com/b", "https://tomshardware.com/c")}
    assert len(ids) == 3


def test_syndicated_identity_never_a_genuine_netloc():
    # The collapsed syndication identity must not collide with any genuine publisher's key.
    synth = collapsed_publisher(_e(url=_YAHOO))
    assert synth != "finance.yahoo.com"
    assert synth != publisher_key(_e(url="https://reuters.com/a"))
