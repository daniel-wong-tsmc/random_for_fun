import pytest
from pydantic import ValidationError
from gpu_agent.wiki.ingest import (
    format_contradiction_detail, parse_contradiction_detail, PageEnrichment)


def test_format_parse_roundtrip():
    detail = format_contradiction_detail(2, [("entity:nvda", "guidance cut"),
                                             ("entity:amd", "share loss")])
    assert detail == ("enriched 2 page(s); contradictions: "
                      "entity:nvda: guidance cut | entity:amd: share loss")
    parsed = parse_contradiction_detail(detail)
    assert parsed["count"] == 2
    assert parsed["contradictions"] == [
        {"pageId": "entity:nvda", "note": "guidance cut"},
        {"pageId": "entity:amd", "note": "share loss"}]


def test_format_parse_no_contradictions():
    detail = format_contradiction_detail(1, [])
    assert detail == "enriched 1 page(s)"
    parsed = parse_contradiction_detail(detail)
    assert parsed == {"count": 1, "contradictions": []}


def test_parse_keeps_entity_colon_and_note_colon():
    # pageId contains ':' (no space); a note may contain ': ' — the FIRST ': ' splits id from note.
    detail = format_contradiction_detail(1, [("entity:nvda", "guidance: cut deep")])
    parsed = parse_contradiction_detail(detail)
    assert parsed["contradictions"] == [{"pageId": "entity:nvda", "note": "guidance: cut deep"}]


def test_salience_bound_rejects_out_of_range():
    with pytest.raises(ValidationError):
        PageEnrichment(pageId="entity:nvda", bodyMarkdown="b", state="s",
                       trajectory="t", salience=5.0)


def test_salience_bound_accepts_edges():
    for s in (0.0, 1.0):
        pe = PageEnrichment(pageId="entity:nvda", bodyMarkdown="b", state="s",
                            trajectory="t", salience=s)
        assert pe.salience == s
