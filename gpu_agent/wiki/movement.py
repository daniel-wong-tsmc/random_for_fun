"""gpu_agent/wiki/movement.py — read-only collector for the brief's store-fed sections
(sub-project 4-5b). Assembles WHAT MOVED (ranked material moves) + STORYLINES (page
state/trajectory) from the wiki store as a plain MarketMovement value. No LLM, no store
write (never calls lint())."""
from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field
from gpu_agent.wiki.lint import score_moves, _contradictions_for, DEFAULT_LINT_CONFIG
from gpu_agent.wiki.lifecycle import partition_canonical


class MovedRow(BaseModel):
    title: str
    findingIds: list[str] = Field(default_factory=list)
    tier: Literal["primary", "secondary"]
    provisional: bool
    newThread: bool
    contradiction: bool
    contradictionNote: str = ""
    stateFrom: Optional[str] = None
    stateTo: Optional[str] = None
    score: float


class StorylineRow(BaseModel):
    title: str
    state: str
    trajectory: str
    lastUpdatedAsOf: str
    salience: float
    provisional: bool


class MarketMovement(BaseModel):
    prevAsOf: Optional[str] = None
    moved: list[MovedRow] = Field(default_factory=list)
    foldedCount: int = 0
    storylines: list[StorylineRow] = Field(default_factory=list)


def _moved_row(m, one_by_id) -> MovedRow:
    st = m.factors.stateTransition or {}
    return MovedRow(
        title=one_by_id.get(m.pageId, m.title),
        findingIds=list(m.contributingFindingIds),
        tier="primary" if m.tierMult >= 0.8 else "secondary",
        provisional=(m.status != "registered"),
        newThread=m.factors.newThread,
        contradiction=m.factors.contradiction,
        contradictionNote=m.factors.contradictionNote,
        stateFrom=st.get("from"),
        stateTo=st.get("to"),
        score=m.score)


def _storyline_rows(entries, *, provisional) -> list[StorylineRow]:
    # Row order is a display concern owned by render_storylines (which sorts each group);
    # the collector returns index order (sorted by category, id).
    return [StorylineRow(title=e.title, state=e.state, trajectory=e.trajectory,
                         lastUpdatedAsOf=e.lastUpdatedAsOf, salience=e.salience,
                         provisional=provisional) for e in entries]


def collect_movement(store, *, as_of, prev_as_of, registry, horizons,
                     config=DEFAULT_LINT_CONFIG) -> MarketMovement:
    """Read-only. WHAT MOVED via diff + score_moves (only when a prior cycle exists);
    STORYLINES via index + partition_canonical. Never writes (never calls lint())."""
    index = store.index()
    one_by_id = {e.id: e.oneLine for e in index}
    moved: list[MovedRow] = []
    folded = 0
    if prev_as_of is not None:
        diff = store.diff(as_of, prev_as_of)
        contradictions = _contradictions_for(store, as_of)
        material, dropped = score_moves(store, diff, contradictions, as_of=as_of,
                                        prev_as_of=prev_as_of, registry=registry,
                                        horizons=horizons, config=config)
        material.sort(key=lambda m: (-m.score, m.pageId))   # byte-stable tiebreak
        moved = [_moved_row(m, one_by_id) for m in material]
        folded = len(dropped)
    registered, provisional = partition_canonical(index)
    storylines = (_storyline_rows(registered, provisional=False)
                  + _storyline_rows(provisional, provisional=True))
    return MarketMovement(prevAsOf=prev_as_of, moved=moved, foldedCount=folded,
                          storylines=storylines)
