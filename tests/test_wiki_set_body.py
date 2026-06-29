import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def test_set_body_replaces_body_and_bumps_as_of(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-26", body="old")
    ws.set_body("entity:nvda", "## NVDA\nnew prose [f-1].\n", as_of="2026-06-28")
    page = ws.get_page("entity:nvda")
    win = ws.window("entity:nvda", 0)
    assert win.body == "## NVDA\nnew prose [f-1].\n"
    assert page.lastUpdatedAsOf == "2026-06-28"
    assert page.title == "NVDA"  # header otherwise intact


def test_set_body_unchanged_is_skipped(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-26", body="same")
    ws.set_body("entity:nvda", "same", as_of="2026-06-28")
    page = ws.get_page("entity:nvda")
    assert page.lastUpdatedAsOf == "2026-06-26"  # no bump: body unchanged


def test_set_body_missing_page_raises(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(PageNotFound):
        ws.set_body("entity:nope", "x", as_of="2026-06-28")
