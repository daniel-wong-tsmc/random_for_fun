from gpu_agent.brief import render_storylines
from gpu_agent.wiki.movement import MarketMovement, MovedRow, StorylineRow


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


def test_storylines_two_groups_arrows_and_order():
    mv = _mv(storylines=[
        _story(title="AMD", state="on-track", trajectory="accelerating", salience=0.5),
        _story(title="NVIDIA moat", state="intact", trajectory="eroding", salience=0.9),
        _story(title="Export controls", state="quiet", trajectory="quiet",
               salience=0.3, provisional=True),
    ])
    out = render_storylines(mv)
    assert "ESTABLISHED" in out
    assert "EARLY (not yet corroborated)" in out
    lines = out.splitlines()
    # registered ordered by salience desc: NVIDIA moat (0.9) before AMD (0.5)
    assert lines.index("    • NVIDIA moat  intact → eroding  (last updated 2026-07)  ▼") \
        < lines.index("    • AMD  on-track → accelerating  (last updated 2026-07)  ▲")
    # provisional group carries the quiet storyline with a · arrow
    assert "    • Export controls  quiet → quiet  (last updated 2026-07)  ·" in out


def test_storylines_none_is_empty_state():
    out = render_storylines(None)
    assert "STORYLINES (tracked over time)" in out
    assert "no wiki store yet" in out


def test_storylines_empty_index_note():
    out = render_storylines(_mv(storylines=[]))
    assert "(no tracked storylines yet)" in out


def test_storylines_one_group_empty_note():
    out = render_storylines(_mv(storylines=[_story(title="AMD")]))  # only registered
    assert "ESTABLISHED" in out and "• AMD" in out
    assert "EARLY (not yet corroborated)" in out
    assert "(none tracked yet)" in out   # empty provisional group
