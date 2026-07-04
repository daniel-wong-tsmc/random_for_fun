# tests/test_publisher.py
from types import SimpleNamespace
from gpu_agent.publisher import publisher_key


def _e(url="", source=""):
    return SimpleNamespace(url=url, source=source)


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
