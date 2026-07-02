from __future__ import annotations
import json
import pathlib
import re
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationError

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


# --- store ---


class ThesisStoreError(Exception):
    """Raised when the on-disk thesis book cannot be trusted: missing, or diverged from
    what replaying history.jsonl produces. Fail loud on drift — never silently repair."""


def apply_record(book: ThesisBook, record: dict) -> ThesisBook:
    """Fold one history record into a book. Pure: returns a new ThesisBook, never mutates
    `book` or `record`. This is the single transition function shared by
    ThesisStore.rebuild() (replay) and the apply engine (Task 4) that writes these same
    records — so replay is always identical to the write path, by construction.

    Judgment records carry the depth fields and (for applied ones) the post-apply
    `conviction` directly, so this function trusts those values rather than re-deriving
    the anti-whipsaw business logic that produced them. Everything else is code-derived
    here from the prior entry state + the record (the spec: streak is code-computed and
    the record shape has no streak field):
      - `streak` (applied records only): reset to 1 when the record's after-conviction
        differs from the entry's prior conviction, or when the verdict's direction is a
        non-zero reversal of a non-zero prior lastDirection; otherwise entry.streak + 1.
        Non-applied records leave streak unchanged.
      - `lastDirection` via DIRECTION[verdict], applied only when non-zero.
      - an `adjusted` verdict's new `statement`, parsed from an `"ADJUSTED:"`-prefixed
        rationale.
    """
    if "event" in record:
        return _apply_lifecycle_record(book, record)
    if "verdict" in record:
        return _apply_judgment_record(book, record)
    raise ThesisStoreError(f"unrecognized history record (no 'event' or 'verdict' key): {record!r}")


def _replace_entry(book: ThesisBook, thesis_id: str, transform) -> ThesisBook:
    entries = []
    found = False
    for entry in book.entries:
        if entry.id == thesis_id:
            entries.append(transform(entry))
            found = True
        else:
            entries.append(entry)
    if not found:
        raise ThesisStoreError(f"history record references unknown thesis id: {thesis_id!r}")
    return book.model_copy(update={"entries": entries})


def _apply_lifecycle_record(book: ThesisBook, record: dict) -> ThesisBook:
    event = record["event"]
    if event == "seeded":
        entries = [ThesisEntry(**e) for e in record["detail"]]
        return book.model_copy(update={"entries": entries})
    if event == "proposed":
        new_entry = ThesisEntry(**record["detail"])
        return book.model_copy(update={"entries": [*book.entries, new_entry]})
    if event == "promoted":
        return _replace_entry(
            book, record["thesisId"],
            lambda e: e.model_copy(update={"status": "registered"}),
        )
    if event == "retired":
        return _replace_entry(
            book, record["thesisId"],
            lambda e: e.model_copy(update={"status": "retired", "conviction": "low"}),
        )
    if event == "challenge-lapsed":
        return _replace_entry(
            book, record["thesisId"],
            lambda e: e.model_copy(update={"pendingChallenge": None}),
        )
    raise ThesisStoreError(f"unknown lifecycle event: {event!r}")


def _apply_judgment_record(book: ThesisBook, record: dict) -> ThesisBook:
    def transform(entry: ThesisEntry) -> ThesisEntry:
        updates: dict = {"lastJudgedAsOf": record["asOf"]}
        if record.get("applied"):
            verdict = record["verdict"]
            statement = entry.statement
            if verdict == "adjusted":
                rationale = record.get("rationale") or ""
                prefix = "ADJUSTED:"
                if rationale.startswith(prefix):
                    statement = rationale[len(prefix):].strip()
            direction = DIRECTION[verdict]
            conviction_changed = record["conviction"] != entry.conviction
            reversal = direction != 0 and entry.lastDirection != 0 and direction != entry.lastDirection
            streak = 1 if (conviction_changed or reversal) else entry.streak + 1
            updates.update({
                "statement": statement,
                "lastVerdict": verdict,
                "conviction": record["conviction"],
                "mechanism": record["mechanism"],
                "falsifiableTrigger": record["falsifiableTrigger"],
                "sensitivity": record["sensitivity"],
                "streak": streak,
                "lastChangedAsOf": record["asOf"],
                "pendingChallenge": None,
            })
            if direction != 0:
                updates["lastDirection"] = direction
        else:
            try:
                updates["pendingChallenge"] = PendingChallenge(
                    verdict=record["verdict"],
                    asOf=record["asOf"],
                    rationale=record["rationale"],
                    findingIds=record["findingIds"],
                )
            except ValidationError as exc:
                raise ThesisStoreError(
                    f"invalid pendingChallenge in history record for thesis "
                    f"{record['thesisId']!r}: {exc}"
                ) from exc
        return entry.model_copy(update=updates)

    return _replace_entry(book, record["thesisId"], transform)


class ThesisStore:
    """book.json + append-only history.jsonl under <store>/theses/<categoryId>."""

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.category_id = self.root.name
        self.book_path = self.root / "book.json"
        self.history_path = self.root / "history.jsonl"

    def exists(self) -> bool:
        return self.book_path.exists()

    def write(self, book: ThesisBook, records: list[dict]) -> None:
        """Append `records` to history.jsonl THEN write book.json. History is the
        temporal source of truth; appending before the book write means a crash between
        the two leaves history ahead of the book, never the reverse."""
        self.root.mkdir(parents=True, exist_ok=True)
        if records:
            with self.history_path.open("a", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, sort_keys=True) + "\n")
        self.book_path.write_text(
            json.dumps(book.model_dump(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def rebuild(self) -> ThesisBook:
        """Fold history.jsonl into a book from scratch. Pure; does not touch book.json."""
        book = ThesisBook(categoryId=self.category_id, entries=[])
        if not self.history_path.exists():
            return book
        with self.history_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                book = apply_record(book, record)
        return book

    def load(self) -> ThesisBook:
        """Read book.json, but only after verifying it equals rebuild()-from-history.
        Raises ThesisStoreError if the book is missing, or if it has drifted from what
        history.jsonl replays to (tamper or a bug) — fail loud, never silently trust
        an unverifiable book."""
        if not self.book_path.exists():
            raise ThesisStoreError(f"thesis book missing: {self.book_path}")
        on_disk = ThesisBook(**json.loads(self.book_path.read_text(encoding="utf-8")))
        rebuilt = self.rebuild()
        if on_disk.model_dump() != rebuilt.model_dump():
            raise ThesisStoreError(
                f"thesis book mismatch for category {self.category_id!r}: "
                f"book.json does not equal the book rebuilt from history.jsonl"
            )
        return on_disk
