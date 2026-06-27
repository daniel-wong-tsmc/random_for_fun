import pytest
from gpu_agent.wiki.page import WikiPage, dump_page, load_page, WikiFormatError


def _page():
    return WikiPage(
        id="theme:cowos-capacity", type="theme", title="CoWoS capacity",
        category="chips.merchant-gpu", state="slipping",
        trajectory="on-track -> slipping", salience=0.8,
        crossRefs=["theme:hbm4", "entity:tsmc"],
        createdAsOf="2026-06-20", lastUpdatedAsOf="2026-06-27",
    )


def test_roundtrip_preserves_header_and_body():
    page = _page()
    body = "## CoWoS\nTSMC slipping [f-1].\n"
    text = dump_page(page, body)
    p2, b2 = load_page(text)
    assert p2 == page
    assert b2 == body
    assert isinstance(p2.salience, float) and p2.salience == 0.8


def test_defaults_roundtrip():
    page = WikiPage(id="entity:nvidia", type="entity", title="NVIDIA",
                    createdAsOf="2026-06-26", lastUpdatedAsOf="2026-06-26")
    p2, b2 = load_page(dump_page(page, ""))
    assert p2 == page and p2.category is None and p2.status == "provisional"


def test_body_with_triple_dash_survives():
    page = _page()
    body = "intro\n---\na horizontal rule in the body\n"
    p2, b2 = load_page(dump_page(page, body))
    assert b2 == body


def test_missing_opening_fence_raises():
    with pytest.raises(WikiFormatError):
        load_page('id: "x"\n')


def test_missing_closing_fence_raises():
    with pytest.raises(WikiFormatError):
        load_page('---\nid: "theme:x"\n')


def test_non_json_value_raises():
    with pytest.raises(WikiFormatError):
        load_page('---\nid: not-json-unquoted\n---\nbody')
