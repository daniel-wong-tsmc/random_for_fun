from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06-26",
        indicatorId="cowosCapacity", side="supply", polarityDemand=0, polaritySupply=-1,
        magnitude=2, entity="tsmc", observedAt="2026-06-26", capturedAt="2026-06-26",
    )


def _store(tmp_path):
    fs = FindingStore(tmp_path / "findings")
    return WikiStore(tmp_path / "wiki", fs), fs


def test_index_empty_on_cold_start(tmp_path):
    ws, fs = _store(tmp_path)
    assert ws.index() == []


def test_index_orders_by_category_then_id(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:b", "theme", "B", category="z", as_of="2026-06-26")
    ws.create_page("theme:a", "theme", "A", category="z", as_of="2026-06-26")
    ws.create_page("entity:m", "entity", "M", category="a", as_of="2026-06-26")
    assert [e.id for e in ws.index()] == ["entity:m", "theme:a", "theme:b"]


def test_index_entry_fields(tmp_path):
    ws, fs = _store(tmp_path)
    fs.append(_finding("f-1"))
    ws.create_page("theme:cowos", "theme", "CoWoS", category="chips", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    ws.record_state("theme:cowos", as_of="2026-06-26", state="slipping", trajectory="t", salience=0.7)
    e = ws.index()[0]
    assert e.observationCount == 1 and e.state == "slipping" and "slipping" in e.oneLine


def test_diff_new_changed_quiet_and_index_moves(tmp_path):
    ws, fs = _store(tmp_path)
    for i in (1, 2, 3):
        fs.append(_finding(f"f-{i}"))
    # Day 1 (2026-06-26): two pages, one observation each
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    ws.create_page("theme:hbm4", "theme", "HBM4", as_of="2026-06-26")
    ws.append_observation("theme:hbm4", "f-2", as_of="2026-06-26")
    # Day 2 (2026-06-27): new page; cowos gets a new obs + a state change; hbm4 stays quiet
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-27")
    ws.append_observation("theme:cowos", "f-3", as_of="2026-06-27")
    ws.record_state("theme:cowos", as_of="2026-06-27", state="slipping", trajectory="t", salience=0.7)
    d = ws.diff("2026-06-27", "2026-06-26")
    assert [p.id for p in d.new_pages] == ["entity:nvda"]
    assert [p.id for p in d.changed_pages] == ["theme:cowos"]
    assert d.quiet_pages == ["theme:hbm4"]
    assert [m.id for m in d.index_moves] == ["theme:cowos"]
    chg = d.changed_pages[0]
    assert chg.newFindingIds == ["f-3"]
    assert chg.stateTransition == {"from": "", "to": "slipping"}


def test_diff_cold_start_is_empty(tmp_path):
    ws, fs = _store(tmp_path)
    d = ws.diff("2026-06-27", "2026-06-26")
    assert d.new_pages == [] and d.changed_pages == [] and d.quiet_pages == [] and d.index_moves == []


def test_diff_salience_only_change_is_index_move_without_state_transition(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.record_state("theme:cowos", as_of="2026-06-26", state="slipping", trajectory="t", salience=0.4)
    # Day 2: same state label + trajectory, higher salience
    ws.record_state("theme:cowos", as_of="2026-06-27", state="slipping", trajectory="t", salience=0.9)
    d = ws.diff("2026-06-27", "2026-06-26")
    assert [m.id for m in d.index_moves] == ["theme:cowos"]
    assert d.index_moves[0].oldSalience == 0.4 and d.index_moves[0].newSalience == 0.9
    move_page = next(p for p in d.changed_pages if p.id == "theme:cowos")
    assert move_page.stateTransition is None
