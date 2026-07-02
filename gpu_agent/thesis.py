from __future__ import annotations
import json
import pathlib
import re
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

# --- models ---

VERDICTS = ("reaffirmed", "strengthened", "weakened", "adjusted", "broken")
DIRECTION = {"strengthened": 1, "weakened": -1, "broken": -1, "reaffirmed": 0, "adjusted": 0}
LENSES = ("demand", "supply", "competitive", "risk")
CONVICTION_RANK = {"low": 0, "medium": 1, "high": 2}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class PendingChallenge(BaseModel):
    verdict: Literal["strengthened", "weakened", "broken"]
    asOf: str
    rationale: str
    findingIds: list[str]


class ThesisEntry(BaseModel):
    id: str
    title: str
    statement: str
    lens: Literal["demand", "supply", "competitive", "risk"]
    status: Literal["registered", "provisional", "retired"] = "registered"
    conviction: Literal["high", "medium", "low"] = "medium"
    lastVerdict: Optional[str] = None  # one of VERDICTS
    lastDirection: Literal[-1, 0, 1] = 0
    pendingChallenge: Optional[PendingChallenge] = None
    streak: int = 0
    mechanism: str
    falsifiableTrigger: str
    sensitivity: str
    createdAsOf: str
    lastChangedAsOf: str
    lastJudgedAsOf: str = ""
    provenance: str = "seeded"


class ThesisBook(BaseModel):
    categoryId: str
    entries: list[ThesisEntry] = Field(default_factory=list)

    def get(self, thesis_id: str) -> ThesisEntry | None:
        for entry in self.entries:
            if entry.id == thesis_id:
                return entry
        return None

    def standing(self) -> list[ThesisEntry]:
        """registered + provisional, not retired."""
        return [e for e in self.entries if e.status != "retired"]


class ThesisJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thesisId: str
    verdict: Literal["reaffirmed", "strengthened", "weakened", "adjusted", "broken"]
    rationale: str
    findingIds: list[str]
    mechanism: str
    falsifiableTrigger: str
    sensitivity: str


class ProposedThesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    statement: str
    lens: Literal["demand", "supply", "competitive", "risk"]
    rationale: str
    findingIds: list[str]
    mechanism: str
    falsifiableTrigger: str
    sensitivity: str


class ThesisAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judgments: list[ThesisJudgment] = Field(default_factory=list)
    proposed: list[ProposedThesis] = Field(default_factory=list)


def thesis_slug(title: str) -> str:
    """Reuses wiki.ingest.slug semantics: lowercase, [^a-z0-9]+ -> '-', strip leading/trailing '-'."""
    s = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"unroutable title (empty slug): {title!r}")
    return s


def seed_book(seed_path, category_id: str, as_of: str) -> ThesisBook:
    """Load the committed seed file into a fresh ThesisBook, all entries at seed defaults."""
    data = json.loads(pathlib.Path(seed_path).read_text(encoding="utf-8"))
    entries = [
        ThesisEntry(
            id=thesis["id"],
            title=thesis["title"],
            statement=thesis["statement"],
            lens=thesis["lens"],
            mechanism=thesis["mechanism"],
            falsifiableTrigger=thesis["falsifiableTrigger"],
            sensitivity=thesis["sensitivity"],
            createdAsOf=as_of,
            lastChangedAsOf=as_of,
        )
        for thesis in data["theses"]
    ]
    return ThesisBook(categoryId=category_id, entries=entries)
