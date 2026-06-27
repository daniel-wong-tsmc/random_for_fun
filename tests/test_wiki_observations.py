import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, FindingNotGated, PageNotFound
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06-26",
        indicatorId="cowosCapacity", side="supply", polarityDemand=0, polaritySupply=-1,
        magnitude=2, entity="tsmc", observedAt="2026-06-26", capturedAt="2026-06-26",
    )


def _store(tmp_path):
    fs = FindingStore(tmp_path / "findings")
    return WikiStore(tmp_path / "wiki", fs), fs


def test_append_observation_requires_gated_finding(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    with pytest.raises(FindingNotGated):
        ws.append_observation("theme:cowos", "f-missing", as_of="2026-06-26")


def test_append_observation_records_and_logs(tmp_path):
    ws, fs = _store(tmp_path)
    fs.append(_finding("f-1"))
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-27")
    obs = ws.observations("theme:cowos")
    assert [o.findingId for o in obs] == ["f-1"]
    assert ws.get_page("theme:cowos").lastUpdatedAsOf == "2026-06-27"


def test_record_state_updates_cache_and_history(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.record_state("theme:cowos", as_of="2026-06-27", state="slipping",
                    trajectory="on-track -> slipping", salience=0.8)
    page = ws.get_page("theme:cowos")
    assert page.state == "slipping" and page.salience == 0.8
    hist = ws.state_history("theme:cowos")
    assert len(hist) == 1 and hist[0].state == "slipping"


def test_window_resolves_last_n_findings(tmp_path):
    ws, fs = _store(tmp_path)
    for i in (1, 2, 3):
        fs.append(_finding(f"f-{i}"))
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-2", as_of="2026-06-27")
    ws.append_observation("theme:cowos", "f-3", as_of="2026-06-28")
    win = ws.window("theme:cowos", 2)
    assert [o.finding.id for o in win.observations] == ["f-2", "f-3"]
    assert win.page.id == "theme:cowos"


def test_observations_on_missing_page_raises(tmp_path):
    ws, fs = _store(tmp_path)
    with pytest.raises(PageNotFound):
        ws.observations("theme:nope")


def test_window_zero_returns_empty(tmp_path):
    ws, fs = _store(tmp_path)
    fs.append(_finding("f-1"))
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    win = ws.window("theme:cowos", 0)
    assert win.observations == []
    assert win.page.id == "theme:cowos"
