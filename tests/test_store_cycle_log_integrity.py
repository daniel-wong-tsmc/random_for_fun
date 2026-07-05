# F74 tripwire — the tracked store/cycle-log.json must hold a finalized journal, never a
# bare cycle-plan skeleton. A run that clobbers the journal (the 2026-07-05 incident: the
# monthly v3 journal, including its gates.sufficiency bypass record, was overwritten in the
# working tree by run-start plan output) goes RED here before the erasure can be committed.
# The plan belongs in the run's work/ dir; the journal is session-authored at finalize.
import json
import pathlib

_PLAN_ENTRY_KEYS = {"category_id", "assignment_path", "status"}
_LOG = pathlib.Path("store/cycle-log.json")


def test_cycle_log_is_finalized_journal_not_plan_skeleton():
    if not _LOG.exists():
        return  # nothing to protect yet (fresh category store)
    journal = json.loads(_LOG.read_text("utf-8"))
    assert journal.get("asOf"), (
        "store/cycle-log.json has no asOf — this is a cycle-plan skeleton, not a finalized "
        "journal. Restore the previous journal (git restore / git checkout) before committing; "
        "plans go in the run's work/ dir (F74)."
    )
    for e in journal.get("entries", []):
        if e.get("status") != "ready":
            continue
        assert set(e) - _PLAN_ENTRY_KEYS, (
            f"{e.get('category_id')}: ready entry carries only bare plan keys — the run "
            "journal (scorecard/gates/answers) is missing. Finalize or restore before "
            "committing (F74)."
        )
