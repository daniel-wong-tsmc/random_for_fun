import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound, DuplicatePage


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def test_create_then_get(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", category="chips.merchant-gpu", as_of="2026-06-26")
    page = ws.get_page("theme:cowos")
    assert page.title == "CoWoS" and page.status == "provisional"
    assert page.createdAsOf == "2026-06-26" and page.lastUpdatedAsOf == "2026-06-26"


def test_create_writes_file_at_typed_path(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvidia", "entity", "NVIDIA", as_of="2026-06-26")
    assert (tmp_path / "wiki" / "entity" / "nvidia.md").exists()


def test_create_duplicate_raises(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    with pytest.raises(DuplicatePage):
        ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-27")


def test_get_missing_raises(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(PageNotFound):
        ws.get_page("theme:nope")


def test_create_logs_event(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    evs = ws.log.read()
    assert evs[0].kind == "create-page" and evs[0].pageId == "theme:cowos"


def test_update_header_allowed_fields(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.update_header("theme:cowos", as_of="2026-06-28", status="registered", crossRefs=["entity:tsmc"])
    page = ws.get_page("theme:cowos")
    assert page.status == "registered" and page.crossRefs == ["entity:tsmc"]
    assert page.lastUpdatedAsOf == "2026-06-28"
    # F30: a header change with actual deltas now also leaves a header-change log event.
    assert [e.kind for e in ws.log.read()] == ["create-page", "header-change"]
    assert "status: provisional -> registered" in ws.log.read()[1].detail


def test_update_header_disallowed_field_raises(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    with pytest.raises(ValueError):
        ws.update_header("theme:cowos", as_of="2026-06-28", salience=0.9)


def test_update_header_missing_page_raises(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(PageNotFound):
        ws.update_header("theme:nope", as_of="2026-06-26", title="X")


def test_create_page_body_roundtrips(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", category="chips.merchant-gpu",
                   as_of="2026-06-26", body="## Heading\nsome prose\n")
    page, body = ws._read("theme:cowos")
    assert body == "## Heading\nsome prose\n"
