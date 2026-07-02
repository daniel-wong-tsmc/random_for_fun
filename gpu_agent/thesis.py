from __future__ import annotations
import json
import pathlib
import re
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gpu_agent.schema.finding import Finding

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


# --- gate ---

# v1 trigger-observable heuristic (spec rule 3): a falsifiableTrigger is deemed to name
# a checkable observable if it contains one of these calendar-cadence words, in addition
# to the registered-indicator-id and any-digit checks in _trigger_names_observable below.
# This is a cheap lexical proxy for "this trigger can be checked against data" — it does
# not verify the named observable is actually measurable, only that the trigger text
# gestures at one. Tighten in a later version if it proves too permissive/strict.
_TRIGGER_KEYWORDS = ("quarter", "qtr", "month", "week", "cycle")


def _normalize_statement(statement: str) -> str:
    """lowercase + whitespace-folded, per spec rule 4's statement-dedup compare."""
    return " ".join(statement.lower().split())


def _trigger_names_observable(trigger: str, registry) -> bool:
    """True iff `trigger` contains a registered indicator id (case-sensitive substring
    of `registry.indicators` keys), OR any digit, OR one of _TRIGGER_KEYWORDS
    (case-insensitive substring)."""
    if any(indicator_id in trigger for indicator_id in registry.indicators):
        return True
    if any(ch.isdigit() for ch in trigger):
        return True
    lowered = trigger.lower()
    return any(keyword in lowered for keyword in _TRIGGER_KEYWORDS)


def _gate_citations(label: str, finding_ids: list[str], findings_by_id: dict[str, Finding]) -> list[str]:
    """Rule 2: findingIds non-empty, and every id resolves in this cycle's findings."""
    errors: list[str] = []
    if not finding_ids:
        errors.append(f"{label}: cites no findings")
        return errors
    for fid in finding_ids:
        if fid not in findings_by_id:
            errors.append(f"{label}: cites unknown finding {fid}")
    return errors


def _gate_depth_fields(label: str, mechanism: str, trigger: str, sensitivity: str, registry) -> list[str]:
    """Rule 3: mechanism/falsifiableTrigger/sensitivity non-empty; a non-empty trigger
    must additionally name an observable per _trigger_names_observable."""
    errors: list[str] = []
    if not mechanism.strip():
        errors.append(f"{label}: missing mechanism")
    if not sensitivity.strip():
        errors.append(f"{label}: missing sensitivity")
    if not trigger.strip():
        errors.append(f"{label}: missing falsifiableTrigger")
    elif not _trigger_names_observable(trigger, registry):
        errors.append(f"{label}: trigger names no observable")
    return errors


def gate_answer(answer: ThesisAnswer, book: ThesisBook,
                 findings_by_id: dict[str, Finding], registry) -> list[str]:
    """Pure, no I/O. [] means the answer is clean; every violation is named by one
    string. Spec rules 1-4:
      1. exactly one judgment per standing (registered/provisional, not retired) thesis
         — a judgment naming a non-standing id (retired, or never seen by the book) is
         "unknown"; a standing id named by >1 judgment is "duplicate"; a standing id
         named by 0 judgments is "missing".
      2. every judgment cites >=1 finding, and every cited id resolves in
         `findings_by_id` (this cycle's gated findings).
      3. depth fields (mechanism/falsifiableTrigger/sensitivity) are non-empty, and the
         trigger names an observable (see _trigger_names_observable).
      4. proposed theses: the slug of the title must not collide with any existing
         entry id (registered, provisional, or retired); the normalized statement must
         not equal any existing entry's statement; and proposals are held to the same
         rule 2/3 citation + depth-field requirements as judgments.
    """
    errors: list[str] = []

    standing_ids = [entry.id for entry in book.standing()]
    standing_id_set = set(standing_ids)

    judged: set[str] = set()
    for judgment in answer.judgments:
        if judgment.thesisId not in standing_id_set:
            errors.append(f"judgment for unknown thesis {judgment.thesisId}")
        elif judgment.thesisId in judged:
            errors.append(f"duplicate judgment for {judgment.thesisId}")
        else:
            judged.add(judgment.thesisId)
        errors.extend(_gate_citations(judgment.thesisId, judgment.findingIds, findings_by_id))
        errors.extend(_gate_depth_fields(
            judgment.thesisId, judgment.mechanism, judgment.falsifiableTrigger,
            judgment.sensitivity, registry,
        ))

    for thesis_id in standing_ids:
        if thesis_id not in judged:
            errors.append(f"no judgment for thesis {thesis_id}")

    existing_ids = {entry.id for entry in book.entries}
    statement_owner: dict[str, str] = {}
    for entry in book.entries:
        statement_owner.setdefault(_normalize_statement(entry.statement), entry.id)

    for proposal in answer.proposed:
        slug = thesis_slug(proposal.title)
        if slug in existing_ids:
            errors.append(f"proposal duplicates thesis id {slug}")
        owner = statement_owner.get(_normalize_statement(proposal.statement))
        if owner is not None:
            errors.append(f"proposal duplicates statement of {owner}")
        errors.extend(_gate_citations(slug, proposal.findingIds, findings_by_id))
        errors.extend(_gate_depth_fields(
            slug, proposal.mechanism, proposal.falsifiableTrigger, proposal.sensitivity, registry,
        ))

    return errors
