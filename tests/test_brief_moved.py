from gpu_agent.brief import render_what_moved
from gpu_agent.wiki.movement import MarketMovement, MovedRow, StorylineRow
from gpu_agent import reader

PROV_LABEL = reader.STATUS_LABEL["provisional"]


def _moved(**kw):
    base = dict(title="NVDA — hot (rising)", findingIds=["f-1"], tier="primary",
                provisional=False, newThread=False, contradiction=False,
                contradictionNote="", stateFrom=None, stateTo=None, score=1.0)
    base.update(kw)
    return MovedRow(**base)


def _story(**kw):
    base = dict(title="AMD", state="on-track", trajectory="accelerating",
                lastUpdatedAsOf="2026-07", salience=0.8, provisional=False)
    base.update(kw)
    return StorylineRow(**base)


def _mv(**kw):
    base = dict(prevAsOf="2026-06", moved=[], foldedCount=0, storylines=[])
    base.update(kw)
    return MarketMovement(**base)


def test_moved_tags_and_arrows():
    mv = _mv(prevAsOf="2026-06", moved=[
        _moved(title="AMD", newThread=True, findingIds=["f-217"], tier="primary"),
        _moved(title="Capex", contradiction=True, contradictionNote="guidance cut",
               findingIds=["f-241"], tier="secondary"),
        _moved(title="RPO", stateFrom="steady", stateTo="accelerating", findingIds=["f-203"]),
        _moved(title="Moat", stateFrom="intact", stateTo="eroding", findingIds=["f-198"]),
        _moved(title="Spot", stateFrom="firm", stateTo="firm", findingIds=["f-9"]),   # neutral kw
        _moved(title="Lead", findingIds=["f-5"]),                                     # indicator-only
    ])
    out = render_what_moved(mv)
    assert "WHAT MOVED SINCE LAST RUN  (vs 2026-06)" in out
    assert "▲ NEW    AMD" in out
    assert "▼ WATCH  Capex" in out and "(guidance cut)" in out
    assert "▲ UP     RPO" in out
    assert "▼ DOWN   Moat" in out
    assert "= CHANGED Spot" in out
    assert "= MOVED  Lead" in out
    assert "steady → accelerating" in out          # stateFrom → stateTo suffix (spec §2①)
    assert "intact → eroding" in out


def test_moved_no_transition_suffix_when_states_absent():
    out = render_what_moved(_mv(moved=[_moved(title="AMD", newThread=True, findingIds=["f-1"])]))
    # only one rendered move row; with no stateFrom/stateTo it carries no "→" transition suffix
    row = [ln for ln in out.splitlines() if "AMD" in ln][0]
    assert "→" not in row


def test_moved_citation_tier_and_provisional():
    mv = _mv(moved=[_moved(title="AMD", findingIds=["f-1", "f-2"], tier="secondary",
                           newThread=True, provisional=True)])
    out = render_what_moved(mv)
    assert "[f-1, f-2] secondary" in out
    assert f"({PROV_LABEL})" in out
    # F67 review fix: bare word "provisional" must not leak into WHAT MOVED (lead section)
    assert "provisional" not in out


def test_moved_folded_footer():
    mv = _mv(moved=[_moved(newThread=True)], foldedCount=3)
    out = render_what_moved(mv)
    assert "(3 lower-materiality items folded — see wiki-lint)" in out


def test_moved_none_is_empty_state():
    out = render_what_moved(None)
    assert "WHAT MOVED SINCE LAST RUN" in out
    assert "no wiki store yet" in out


def test_moved_no_prior_note():
    out = render_what_moved(_mv(prevAsOf=None))
    assert "no prior cycle to compare" in out
    assert "(vs " not in out


def test_moved_empty_when_no_moves():
    out = render_what_moved(_mv(prevAsOf="2026-06", moved=[], foldedCount=0))
    assert "(no material moves this cycle)" in out
