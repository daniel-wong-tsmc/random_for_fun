import json

import pytest

from gpu_agent.thesis import (
    PendingChallenge,
    ThesisStore,
    ThesisStoreError,
    seed_book,
)

SEED_PATH = "registry/theses.chips.merchant-gpu.json"
CATEGORY_ID = "chips.merchant-gpu"
AS_OF_1 = "2026-07-03"
AS_OF_2 = "2026-07-10"


def _seeded_record(book, as_of):
    return {
        "asOf": as_of,
        "event": "seeded",
        "thesisId": "",
        "detail": [e.model_dump() for e in book.entries],
    }


def _judgment_record(entry_id, *, as_of, verdict="reaffirmed", applied=True,
                      conviction="medium", mechanism="m", trigger="t",
                      sensitivity="s", rationale="r", finding_ids=None):
    # Spec §1 record shape verbatim — NO streak field: streak is code-computed
    # by apply_record from the prior entry state + this record.
    return {
        "asOf": as_of,
        "thesisId": entry_id,
        "verdict": verdict,
        "applied": applied,
        "conviction": conviction,
        "rationale": rationale,
        "findingIds": finding_ids or ["f-1"],
        "mechanism": mechanism,
        "falsifiableTrigger": trigger,
        "sensitivity": sensitivity,
        "note": f"{verdict} applied={applied}",
    }


def _apply_judgment_to_book(book, entry_id, **kwargs):
    """Build the post-apply book the same way apply_answer (Task 4) would, so the
    test's `book` argument to write() matches what the corresponding record implies."""
    entries = []
    for e in book.entries:
        if e.id == entry_id:
            update = {
                "lastVerdict": kwargs["verdict"],
                "conviction": kwargs["conviction"],
                "mechanism": kwargs["mechanism"],
                "falsifiableTrigger": kwargs["trigger"],
                "sensitivity": kwargs["sensitivity"],
                "streak": kwargs["streak"],
                "lastChangedAsOf": kwargs["as_of"],
                "lastJudgedAsOf": kwargs["as_of"],
                "pendingChallenge": None,
            }
            entries.append(e.model_copy(update=update))
        else:
            entries.append(e)
    return book.model_copy(update={"entries": entries})


def test_write_then_load_round_trips(tmp_path):
    book = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    record = _seeded_record(book, AS_OF_1)

    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.write(book, [record])

    loaded = store.load()
    assert loaded.model_dump() == book.model_dump()


def test_load_on_missing_book_raises(tmp_path):
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    assert store.exists() is False
    with pytest.raises(ThesisStoreError):
        store.load()


def test_load_raises_on_tamper_mentioning_mismatch(tmp_path):
    book = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    record = _seeded_record(book, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.write(book, [record])

    on_disk = json.loads(store.book_path.read_text(encoding="utf-8"))
    on_disk["entries"][0]["conviction"] = "high"
    assert on_disk["entries"][0]["conviction"] != book.entries[0].conviction
    store.book_path.write_text(json.dumps(on_disk), encoding="utf-8")

    with pytest.raises(ThesisStoreError) as excinfo:
        store.load()
    assert "mismatch" in str(excinfo.value)


def test_history_is_append_only(tmp_path):
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    seeded = _seeded_record(book1, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.write(book1, [seeded])

    lines_after_first = store.history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after_first) == 1

    jr = _judgment_record(
        "nvda-demand-durability", as_of=AS_OF_2, verdict="reaffirmed",
        applied=True, conviction="medium",
        mechanism=book1.get("nvda-demand-durability").mechanism,
        trigger=book1.get("nvda-demand-durability").falsifiableTrigger,
        sensitivity=book1.get("nvda-demand-durability").sensitivity,
    )
    book2 = _apply_judgment_to_book(
        book1, "nvda-demand-durability", verdict="reaffirmed", conviction="medium",
        mechanism=jr["mechanism"], trigger=jr["falsifiableTrigger"],
        sensitivity=jr["sensitivity"], streak=1, as_of=AS_OF_2,
    )
    store.write(book2, [jr])

    lines_after_second = store.history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after_second) == 2
    assert lines_after_second[0] == lines_after_first[0]


def test_rebuild_from_history_equals_last_written_book(tmp_path):
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    seeded = _seeded_record(book1, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.write(book1, [seeded])

    prior = book1.get("nvda-demand-durability")
    jr = _judgment_record(
        "nvda-demand-durability", as_of=AS_OF_2, verdict="strengthened",
        applied=True, conviction="high",
        mechanism=prior.mechanism, trigger=prior.falsifiableTrigger,
        sensitivity=prior.sensitivity,
    )
    # expected streak: conviction changed (medium -> high) => reset to 1
    book2 = _apply_judgment_to_book(
        book1, "nvda-demand-durability", verdict="strengthened", conviction="high",
        mechanism=jr["mechanism"], trigger=jr["falsifiableTrigger"],
        sensitivity=jr["sensitivity"], streak=1, as_of=AS_OF_2,
    )
    # lastDirection also moves for a non-neutral verdict, per DIRECTION map
    book2 = book2.model_copy(update={
        "entries": [
            e.model_copy(update={"lastDirection": 1}) if e.id == "nvda-demand-durability" else e
            for e in book2.entries
        ]
    })
    store.write(book2, [jr])

    rebuilt = store.rebuild()
    assert rebuilt.model_dump() == book2.model_dump()

    loaded = store.load()
    assert loaded.model_dump() == book2.model_dump()


def test_rebuild_handles_full_lifecycle_vocabulary(tmp_path):
    """apply_record must handle every lifecycle event the plan names, since Task 4's apply
    engine shares this exact transition function — a silently-skipped event would drift."""
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    records = [_seeded_record(book1, AS_OF_1)]

    # a non-applied (deferred) reversal sets pendingChallenge
    deferred = _judgment_record(
        "amd-credible-second-source", as_of=AS_OF_2, verdict="weakened",
        applied=False, rationale="deferred: secondary-only reversal",
        finding_ids=["f-2"],
    )
    records.append(deferred)

    # a challenge that lapses next cycle
    records.append({
        "asOf": AS_OF_2, "event": "challenge-lapsed",
        "thesisId": "amd-credible-second-source", "detail": None,
    })

    # a new provisional proposal
    proposed_entry = book1.get("nvda-demand-durability").model_copy(update={
        "id": "new-thesis", "title": "New thesis", "status": "provisional",
        "conviction": "low", "provenance": f"proposed@{AS_OF_2}",
    })
    records.append({
        "asOf": AS_OF_2, "event": "proposed", "thesisId": "new-thesis",
        "detail": proposed_entry.model_dump(),
    })

    # that proposal is promoted
    records.append({
        "asOf": AS_OF_2, "event": "promoted", "thesisId": "new-thesis", "detail": None,
    })

    # a thesis breaks and retires
    records.append({
        "asOf": AS_OF_2, "event": "retired", "thesisId": "export-control-exposure",
        "detail": None,
    })

    # Append every record directly to history.jsonl — this test targets rebuild()'s
    # replay of the lifecycle vocabulary, not write()'s book/history pairing.
    store.root.mkdir(parents=True, exist_ok=True)
    with store.history_path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    rebuilt = store.rebuild()

    amd = rebuilt.get("amd-credible-second-source")
    assert amd.pendingChallenge is None

    new_thesis = rebuilt.get("new-thesis")
    assert new_thesis is not None
    assert new_thesis.status == "registered"

    export = rebuilt.get("export-control-exposure")
    assert export.status == "retired"
    assert export.conviction == "low"


def test_unknown_event_type_fails_loud(tmp_path):
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.root.mkdir(parents=True, exist_ok=True)
    with store.history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"asOf": AS_OF_1, "event": "mystery", "thesisId": "x", "detail": None}) + "\n")

    with pytest.raises(ThesisStoreError):
        store.rebuild()


def test_pending_challenge_round_trips_via_load(tmp_path):
    """A book with pendingChallenge SET must survive write -> load: the challenge must be
    a validated PendingChallenge model on both sides of the rebuild comparison."""
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.write(book1, [_seeded_record(book1, AS_OF_1)])

    deferred = _judgment_record(
        "amd-credible-second-source", as_of=AS_OF_2, verdict="weakened",
        applied=False, rationale="deferred: secondary-only reversal", finding_ids=["f-2"],
    )
    challenge = PendingChallenge(
        verdict="weakened", asOf=AS_OF_2,
        rationale="deferred: secondary-only reversal", findingIds=["f-2"],
    )
    book2 = book1.model_copy(update={
        "entries": [
            e.model_copy(update={"pendingChallenge": challenge, "lastJudgedAsOf": AS_OF_2})
            if e.id == "amd-credible-second-source" else e
            for e in book1.entries
        ]
    })
    store.write(book2, [deferred])

    loaded = store.load()
    amd = loaded.get("amd-credible-second-source")
    assert amd.pendingChallenge is not None
    assert isinstance(amd.pendingChallenge, PendingChallenge)
    assert amd.pendingChallenge.model_dump() == challenge.model_dump()
    # streak untouched by a non-applied record
    assert amd.streak == 0


def test_invalid_pending_challenge_verdict_fails_loud(tmp_path):
    """An applied=false record whose verdict is outside PendingChallenge's Literal
    (e.g. 'reaffirmed') must raise ThesisStoreError, not be silently accepted."""
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    records = [
        _seeded_record(book1, AS_OF_1),
        _judgment_record(
            "amd-credible-second-source", as_of=AS_OF_2,
            verdict="reaffirmed", applied=False,
        ),
    ]
    store.root.mkdir(parents=True, exist_ok=True)
    with store.history_path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    with pytest.raises(ThesisStoreError):
        store.rebuild()


def test_adjusted_rewrites_statement_on_rebuild(tmp_path):
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    records = [
        _seeded_record(book1, AS_OF_1),
        _judgment_record(
            "pricing-power-persistence", as_of=AS_OF_2, verdict="adjusted",
            applied=True, conviction="medium",
            rationale="ADJUSTED: GPU rental prices hold up only in the top-tier SKUs.",
        ),
    ]
    store.root.mkdir(parents=True, exist_ok=True)
    with store.history_path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    rebuilt = store.rebuild()
    entry = rebuilt.get("pricing-power-persistence")
    assert entry.statement == "GPU rental prices hold up only in the top-tier SKUs."
    assert entry.lastVerdict == "adjusted"
    assert entry.lastDirection == 0  # adjusted is direction-neutral
    assert entry.streak == 1  # conviction unchanged, no reversal: 0 + 1


def test_streak_is_code_derived_from_record_and_prior_state(tmp_path):
    """streak is NOT in the record contract; apply_record derives it: reset to 1 on a
    conviction change or a non-zero direction reversal, else prior streak + 1."""
    thesis_id = "nvda-demand-durability"
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.root.mkdir(parents=True, exist_ok=True)

    def append(record):
        with store.history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    append(_seeded_record(book1, AS_OF_1))

    # two reaffirmed cycles, conviction unchanged -> streak increments 1, 2
    append(_judgment_record(thesis_id, as_of="2026-07-10", verdict="reaffirmed", conviction="medium"))
    assert store.rebuild().get(thesis_id).streak == 1
    append(_judgment_record(thesis_id, as_of="2026-07-17", verdict="reaffirmed", conviction="medium"))
    assert store.rebuild().get(thesis_id).streak == 2

    # strengthened WITH conviction change -> reset to 1, lastDirection +1
    append(_judgment_record(thesis_id, as_of="2026-07-24", verdict="strengthened", conviction="high"))
    entry = store.rebuild().get(thesis_id)
    assert entry.streak == 1
    assert entry.lastDirection == 1

    # same direction, conviction unchanged -> increments to 2
    append(_judgment_record(thesis_id, as_of="2026-07-31", verdict="strengthened", conviction="high"))
    assert store.rebuild().get(thesis_id).streak == 2

    # pure direction reversal (conviction unchanged) -> reset to 1, lastDirection -1
    append(_judgment_record(thesis_id, as_of="2026-08-07", verdict="weakened", conviction="high"))
    entry = store.rebuild().get(thesis_id)
    assert entry.streak == 1
    assert entry.lastDirection == -1
