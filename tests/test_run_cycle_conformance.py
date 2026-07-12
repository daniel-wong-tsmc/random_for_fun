"""F83 - orchestration-prose conformance pin for unattended cycles.

Unattended scheduled dailies went LIVE 2026-07-12, but `run-cycle`'s
session-orchestrated behavior is skill PROSE that no test pinned. A drifted skill
edit, or a session skipping a prescribed step, could fail SILENT - the F74 clobber
and F71 bypass proved that happens in practice. This suite drives the $0 recorded
path end-to-end (`pipeline --recorded*` over committed `fixtures/recorded/*`) into a
temp store and asserts the machine-checkable prescriptions of
`.claude/skills/run-cycle/SKILL.md`:

  1. Journal shape - a finalized cycle-log entry carries asOf/mode/capturedAt/gates
     and is never a bare plan skeleton (checked via the existing cycle models + the
     F74 helper, not a hand-copied key list).
  2. Gate order + presence - extraction -> judgment(sufficiency) -> thesis -> report
     in the prescription; each gate recorded in the journal; no whole-run bypass
     flag on the live `pipeline` verb (F75: `--no-sufficiency` is gone).
  3. Nothing silent - a selected-but-unassigned category is a logged SKIPPED line,
     and a recorded-answer/count mismatch fails LOUD (exit 2), never a silent partial.
  4. Write discipline - the recorded pipeline writes ONLY the scorecard carve-out;
     `cycle-plan --out` refuses to clobber a finalized journal (F74).
  5. Prose<->pin sync - the Procedure step list is pinned as a CONSTANT here, and
     SKILL.md carries a matching fingerprint comment; either drifting alone fails loud
     (the compliance-matrix rot-lint pattern).

HONEST RESIDUAL - what a $0 recorded replay CANNOT pin (do not read this suite as
full coverage of run-cycle):
  R1. Live gather quality (3a) - real-web selection/recency/provenance: no surrogate.
  R2. Brain reasoning + the voice-lint/sufficiency re-dispatch loop (3b/3c/3e) - the
      pin replays FROZEN recorded answers, so it pins the gate/score plumbing, never
      the reasoning quality or the re-dispatch judgment.
  R3. Thesis gate live execution (3e) - no committed thesis-answer fixture exists and
      hand-authoring a brain answer is forbidden; thesis is pinned as a PRESENCE+ORDER
      step and a recorded journal outcome only, not driven live.
  R4. DROPPED / UNREGISTERED-ENTITY live emission - clean fixtures do not trip them;
      forcing them needs a malformed/out-of-taxonomy brain answer (forbidden). The
      no-silent contract is proven instead via the SKIPPED and count-mismatch paths.
  R5. Commit/push etiquette, the Step-2 cost-confirmation gate, and F67 report-prose
      surfacing - session-judgment / interactive, not drivable by a $0 replay.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pytest

from gpu_agent.cli import main, _is_bare_plan, _PLAN_ENTRY_KEYS
from gpu_agent.cycle import CyclePlan, CycleEntry
from gpu_agent.registry.structure import Taxonomy

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "run-cycle" / "SKILL.md"
TAXONOMY = ROOT / "docs" / "taxonomy.json"
ASSIGNMENTS_DIR = ROOT / "fixtures"

# Committed recorded artifacts + config (never hand-authored - F83 constraint).
DOCS = str(ROOT / "fixtures" / "raw")
ASSIGNMENT = str(ROOT / "fixtures" / "asg.chips.merchant-gpu.json")
RECORDED_EXTRACT = str(ROOT / "fixtures" / "recorded" / "extract-nvda.json")
RECORDED_JUDGE = str(ROOT / "fixtures" / "recorded" / "judge-nvda.json")
CATEGORY = "chips.merchant-gpu"
AS_OF = "2026-06"
CAPTURED_AT = "2026-06-12T00:00:00Z"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _run_recorded_pipeline(store: pathlib.Path) -> pathlib.Path:
    """Drive the $0 recorded pipeline into `store`; return the written scorecard path.

    Mirrors run-cycle Step 3(d): the frozen brain re-gates the recorded extract +
    judge answers, scores, and persists ONE scorecard. --no-voice-lint matches the
    legacy-fixture note in test_pipeline_integration (the committed judge-nvda answer
    predates the F67 acronym allowlist)."""
    rc = main(["pipeline", "--docs", DOCS, "--assignment", ASSIGNMENT,
               "--as-of", AS_OF, "--captured-at", CAPTURED_AT, "--samples", "3",
               "--recorded-extract", RECORDED_EXTRACT, "--recorded-judge", RECORDED_JUDGE,
               "--no-voice-lint", "--out", str(store)])
    assert rc == 0, f"recorded pipeline exited {rc}, expected 0"
    written = sorted((store / CATEGORY).glob(f"{AS_OF}-v*.json"))
    assert written, "recorded pipeline wrote no scorecard"
    return written[0]


def _finalized_journal(plan: CyclePlan, scorecard: pathlib.Path) -> dict:
    """Author a finalized cycle-log journal the way run-cycle Step 6 prescribes:
    start from the plan, add the required run header (asOf/mode/capturedAt), and
    enrich the ready entry into a `done` entry carrying scorecard + gate outcomes +
    stage statuses. Ties dmi/smi to the REAL written scorecard so this is the recorded
    run's journal, not a free-floating dict."""
    sc = json.loads(scorecard.read_text("utf-8"))
    ds = sc["demandSupply"]
    payload = plan.model_dump()
    payload.update({"asOf": AS_OF, "mode": "recorded", "capturedAt": CAPTURED_AT})
    for entry in payload["entries"]:
        if entry["status"] != "ready":
            continue
        entry.update({
            "status": "done",
            "scorecard": str(scorecard),
            "dmi": ds["dmiContribution"],
            "smi": ds["smiContribution"],
            "gates": {
                "extract": "gated, 0 dropped",
                "unregisteredEntity": {"count": 0, "names": []},
                "voiceLint": "bypassed (legacy fixture)",
                "sufficiency": "passed",
                "thesis": "skipped (no recorded thesis fixture - residual R3)",
            },
            "stageStatus": {"category": "done", "thesis": "skipped",
                            "layer": "deferred", "main": "deferred"},
        })
    return payload


def _title_head(text: str) -> str:
    """Normalize a step heading to its leading title token (robust to prose edits
    inside the step body, sensitive to a rename/reorder of the step itself)."""
    for sep in (" — ", " - ", ".", "(", "**", ":"):
        idx = text.find(sep)
        if idx != -1:
            text = text[:idx]
    return re.sub(r"\s+", " ", text).strip().lower()


_NUM_RE = re.compile(r"^### (\d+)\.\s+(.*)$")
_SUB_RE = re.compile(r"^\*\*\(([a-z0-9-]+)\)\s+(.*)$")


def _parse_procedure_steps(text: str) -> tuple[tuple[str, str], ...]:
    """Ordered (step_id, title_head) pairs from the SKILL's `## Procedure` section
    (numbered `### N.` steps + `**(label) Title**` sub-steps), bounded before
    `## Daily mode`. The fingerprint comment is an HTML comment - never matched."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "## Procedure")
    # bound to the Procedure section: the next top-level `## ` header (Daily mode)
    end = next(i for i in range(start + 1, len(lines))
               if lines[i].startswith("## "))
    steps: list[tuple[str, str]] = []
    for line in lines[start:end]:
        m = _NUM_RE.match(line) or _SUB_RE.match(line)
        if m:
            steps.append((m.group(1), _title_head(m.group(2))))
    return tuple(steps)


# The pinned Procedure step list. If a SKILL edit legitimately changes the steps,
# regenerate this AND the SKILL.md fingerprint comment together (that lockstep is
# the whole point of the sync guard).
EXPECTED_STEPS: tuple[tuple[str, str], ...] = (
    ("1", "resolve the scope to a cycle plan"),
    ("2", "preview / confirm gate"),
    ("3", "run each `ready` category"),
    ("a0", "store coverage"),
    ("a", "gather"),
    ("b", "extraction"),
    ("b2", "corpus assembly"),
    ("c", "judgment"),
    ("d", "score + store"),
    ("d2", "write-back"),
    ("e", "thesis"),
    ("f", "render the executive report"),
    ("4", "layer stage"),
    ("5", "main stage"),
    ("6", "finalize the cycle log"),
    ("7", "report"),
)

_FINGERPRINT_RE = re.compile(r"run-cycle-step-fingerprint:\s*sha256=([0-9a-f]{64})")


def _expected_fingerprint() -> str:
    return hashlib.sha256(repr(EXPECTED_STEPS).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# 1 + 4. Write discipline: the recorded pipeline writes ONLY the scorecard carve-out
# --------------------------------------------------------------------------- #
def test_recorded_pipeline_writes_only_the_scorecard_carveout(tmp_path):
    store = tmp_path / "store"
    scorecard = _run_recorded_pipeline(store)
    written = [p for p in store.rglob("*") if p.is_file()]
    assert written == [scorecard], (
        f"recorded pipeline touched more than the scorecard carve-out: "
        f"{[str(p.relative_to(store)) for p in written]}")
    assert scorecard.name == f"{AS_OF}-v1.json"
    assert scorecard.parent.name == CATEGORY
    # the F74 journal file must never be born of a recorded score run
    assert not (store / "cycle-log.json").exists()


def test_cycle_plan_refuses_to_clobber_finalized_journal(tmp_path):
    finalized = tmp_path / "cycle-log.json"
    finalized.write_text(json.dumps({
        "scope": f"category:{CATEGORY}", "asOf": AS_OF, "mode": "recorded",
        "capturedAt": CAPTURED_AT,
        "entries": [{"category_id": CATEGORY, "assignment_path": ASSIGNMENT,
                     "status": "done", "scorecard": "x", "gates": {}}],
        "stages": [],
    }), "utf-8")
    rc = main(["cycle-plan", "--scope", f"category:{CATEGORY}",
               "--assignments", str(ASSIGNMENTS_DIR), "--taxonomy", str(TAXONOMY),
               "--out", str(finalized)])
    assert rc == 1, "cycle-plan must REFUSE (exit 1) to overwrite a finalized journal (F74)"
    # the finalized journal survives untouched
    survivor = json.loads(finalized.read_text("utf-8"))
    assert survivor["entries"][0]["status"] == "done"


# --------------------------------------------------------------------------- #
# 1. Journal shape via the existing models + the F74 no-bare-ready rule
# --------------------------------------------------------------------------- #
def test_finalized_journal_shape(tmp_path):
    store = tmp_path / "store"
    scorecard = _run_recorded_pipeline(store)
    plan = CyclePlan(
        scope=f"category:{CATEGORY}",
        entries=[CycleEntry(category_id=CATEGORY, assignment_path=ASSIGNMENT,
                            status="ready")])
    journal = _finalized_journal(plan, scorecard)

    # F74 tripwire rule #1: the required run header (no asOf == a bare plan skeleton).
    assert journal.get("asOf"), "finalized journal missing asOf (reads as a plan skeleton)"
    assert journal.get("mode") and journal.get("capturedAt")

    # F74 tripwire rule #2: a done/ready entry must carry more than the bare plan keys.
    entry = journal["entries"][0]
    assert set(entry) - _PLAN_ENTRY_KEYS, (
        "journal entry carries only bare plan keys - the run journal "
        "(scorecard/gates/answers) is missing (F74)")

    # gate outcomes are recorded, and tied to the REAL scorecard the run wrote.
    gates = entry["gates"]
    assert {"extract", "sufficiency", "voiceLint", "thesis"} <= set(gates)
    assert pathlib.Path(entry["scorecard"]).exists()
    sc = json.loads(scorecard.read_text("utf-8"))
    assert entry["dmi"] == sc["demandSupply"]["dmiContribution"]
    assert entry["smi"] == sc["demandSupply"]["smiContribution"]

    # the whole payload is not itself a bare plan skeleton
    assert not _is_bare_plan(journal)


# --------------------------------------------------------------------------- #
# 2. Gate order + presence + no whole-run bypass (F75)
# --------------------------------------------------------------------------- #
def test_pipeline_has_no_whole_run_sufficiency_bypass():
    # F75 (contract v1.4): the whole-run --no-sufficiency escape hatch was REMOVED;
    # the sufficiency gate always runs on the live/recorded path. argparse rejects it.
    with pytest.raises(SystemExit) as exc:
        main(["pipeline", "--no-sufficiency", "--docs", DOCS,
              "--assignment", ASSIGNMENT, "--as-of", AS_OF])
    assert exc.value.code == 2


def test_gate_order_in_prescription():
    steps = _parse_procedure_steps(SKILL.read_text("utf-8"))
    titles = [t for _, t in steps]

    def idx(substr: str) -> int:
        matches = [i for i, t in enumerate(titles) if substr in t]
        assert matches, f"no Procedure step whose title contains {substr!r}"
        return matches[0]

    # extraction -> judgment(sufficiency evaluated) -> thesis -> report
    assert idx("extraction") < idx("judgment") < idx("thesis") < idx("render")


def test_journal_records_each_gate_outcome(tmp_path):
    store = tmp_path / "store"
    scorecard = _run_recorded_pipeline(store)
    plan = CyclePlan(scope=f"category:{CATEGORY}",
                     entries=[CycleEntry(category_id=CATEGORY,
                                         assignment_path=ASSIGNMENT, status="ready")])
    gates = _finalized_journal(plan, scorecard)["entries"][0]["gates"]
    for gate in ("extract", "sufficiency", "voiceLint", "thesis"):
        assert gates.get(gate), f"gate {gate!r} outcome not recorded in the journal"


# --------------------------------------------------------------------------- #
# 3. Nothing silent
# --------------------------------------------------------------------------- #
def test_cycle_plan_surfaces_every_unassigned_category(capsys):
    rc = main(["cycle-plan", "--scope", "all",
               "--assignments", str(ASSIGNMENTS_DIR), "--taxonomy", str(TAXONOMY)])
    assert rc == 0
    err = capsys.readouterr().err
    skipped = [ln for ln in err.splitlines() if ln.startswith("SKIPPED ")]

    taxonomy = Taxonomy.load(str(TAXONOMY))
    expected = [c for c in taxonomy.all_categories()
                if not (ASSIGNMENTS_DIR / f"asg.{c}.json").exists()]
    assert len(skipped) == len(expected) > 0, (
        f"cycle-plan silently dropped categories: {len(skipped)} SKIPPED lines "
        f"for {len(expected)} unassigned categories (no-silent-truncation, Part 38)")


def test_recorded_answer_count_mismatch_fails_loud(capsys):
    # judge-nvda has 3 answers; fixtures/raw has 1 doc -> a loud exit 2, never a
    # silent partial extraction.
    rc = main(["extract", "--recorded", RECORDED_JUDGE, "--docs", DOCS, "--as-of", AS_OF])
    assert rc == 2
    err = capsys.readouterr().err
    assert "recorded answers (3) != documents (1)" in err


# --------------------------------------------------------------------------- #
# 5. Prose <-> pin sync guard
# --------------------------------------------------------------------------- #
def test_procedure_step_list_matches_pinned_constant():
    steps = _parse_procedure_steps(SKILL.read_text("utf-8"))
    assert steps == EXPECTED_STEPS, (
        "run-cycle Procedure step list drifted from the pinned constant. If the "
        "change is intentional, update EXPECTED_STEPS and the SKILL.md "
        "run-cycle-step-fingerprint comment together.")


def test_skill_fingerprint_in_sync():
    text = SKILL.read_text("utf-8")
    m = _FINGERPRINT_RE.search(text)
    assert m, "SKILL.md is missing the run-cycle-step-fingerprint comment (F83 pin)"
    assert m.group(1) == _expected_fingerprint(), (
        "SKILL.md fingerprint comment is out of sync with the pinned step list - "
        "the step list changed without regenerating the fingerprint (or vice versa).")
