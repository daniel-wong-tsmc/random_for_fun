"""Tests for Task 4 of sub-project 5-2 (output surgery): page reorder + words-first
STATE + index demotion + CLI thesis-book loading.

Five scenarios, per the task brief:
  1. section order — THE CALLS < STATE OF THE MARKET < WHY < WHAT MOVED < TRUST & COVERAGE.
  2. raw 'DMI 0.' appears ONLY after the TRUST & COVERAGE heading; the STATE section
     speaks bands (words first, Part 17).
  3. thesis_book=None -> THE CALLS/WHY render honest empty states; still byte-stable.
  4. CLI: gpu-agent report over a store WITH a seeded+judged thesis book shows THE CALLS
     content; without a theses store, the honest empty-state line.
  5. byte-determinism: two renders of the same inputs are identical.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from gpu_agent.report import render_report
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence
from gpu_agent.schema.scorecard import (
    CategoryStatus, DemandSupply, Divergence, MarketIndices, Scorecard,
)
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.wiki.movement import MarketMovement, StorylineRow

PY = sys.executable
CLEAN_ANSWER = Path("tests/fixtures/thesis-answer-clean.json")
GOLDEN_FINDINGS = "fixtures/golden/findings.json"
POSTB_SCORECARD = "fixtures/report/postb-scorecard.json"


# ── Test helpers ─────────────────────────────────────────────────────────────

def _ds(dmi: float = 0.07, smi: float = 0.05) -> DemandSupply:
    return DemandSupply(dmiContribution=dmi, smiContribution=smi)


def _sc(dmi: float = 0.07, smi: float = 0.05,
        indices: MarketIndices | None = None,
        category_status: CategoryStatus | None = None,
        findings: list | None = None) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf="2026-07",
        findings=findings or [],
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
        indices=indices,
        categoryStatus=category_status,
    )


def _catstat():
    return CategoryStatus(rating="Strong", direction="improving",
                          bottleneck="advanced packaging (CoWoS)",
                          reason="demand outruns the packaging ramp")


def _rich_sc():
    ix = MarketIndices(momentum=_ds(dmi=0.07, smi=0.05), outlook=_ds(dmi=0.0, smi=0.0),
                       divergence=Divergence(state="insufficient-coverage", sdgiGap=0.0,
                                             outlookFindingCount=0, momentumFindingCount=3,
                                             note="no leading findings yet"))
    return _sc(dmi=0.07, smi=0.05, indices=ix, category_status=_catstat())


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _entry(entry_id="demand-durability", **overrides):
    fields = dict(
        id=entry_id, title="Demand outruns capacity",
        statement="Demand keeps outrunning shipment capacity.", lens="demand",
        status="registered", conviction="high", lastVerdict="reaffirmed",
        lastDirection=0, streak=3, mechanism="Backlog grows faster than shipments.",
        falsifiableTrigger="Backlog/RPO growth falls below shipment growth for 2 quarters.",
        sensitivity="Hyperscaler capex guidance.",
        createdAsOf="2026-06", lastChangedAsOf="2026-06", lastJudgedAsOf="2026-06",
    )
    fields.update(overrides)
    return ThesisEntry(**fields)


def _book():
    return ThesisBook(categoryId="chips.merchant-gpu", entries=[_entry()])


def _movement():
    return MarketMovement(prevAsOf=None, moved=[], foldedCount=0, storylines=[
        StorylineRow(title="AMD", state="on-track", trajectory="accelerating",
                     lastUpdatedAsOf="2026-07", salience=0.8, provisional=False)])


def _find_all(haystack: str, needle: str) -> list[int]:
    idxs, start = [], 0
    while True:
        i = haystack.find(needle, start)
        if i == -1:
            return idxs
        idxs.append(i)
        start = i + 1


# ── 1. section order ──────────────────────────────────────────────────────────

def test_section_order_calls_state_why_moved_trust():
    out = render_report(_rich_sc(), None, _reg(), render_ts="fixed", thesis_book=_book())
    assert (out.index("THE CALLS") < out.index("STATE OF THE MARKET")
            < out.index("WHY") < out.index("WHAT MOVED") < out.index("TRUST & COVERAGE"))


# ── 2. raw index demotion + words-first STATE ─────────────────────────────────

def test_dmi_raw_value_appears_only_after_trust_and_coverage_heading():
    prior = _sc(dmi=0.04, smi=0.05)
    sc = _rich_sc()   # dmi=0.07 -> "DMI 0.070" once the raw table renders it
    out = render_report(sc, prior, _reg(), render_ts="fixed")
    i_trust = out.index("TRUST & COVERAGE")
    occurrences = _find_all(out, "DMI 0.")
    assert occurrences, "expected the raw DMI value to appear in the trust footer table"
    for idx in occurrences:
        assert idx > i_trust, (
            f"raw 'DMI 0.' value leaked before the TRUST & COVERAGE heading at index {idx}"
        )


def test_state_section_speaks_bands_not_raw_numbers():
    prior = _sc(dmi=0.04, smi=0.05)
    sc = _rich_sc()
    out = render_report(sc, prior, _reg(), render_ts="fixed")
    i_state = out.index("STATE OF THE MARKET")
    i_why = out.index("WHY")
    state_section = out[i_state:i_why]
    assert "Demand: " in state_section
    assert any(marker in state_section for marker in ("(was ", "(no prior)"))
    # a real band word (not a raw index) backs the Demand: line
    demand_line = next(ln for ln in state_section.splitlines() if "Demand: " in ln)
    assert any(w in demand_line for w in
               ("ACCELERATING", "FIRM", "FLAT", "SOFTENING", "CONTRACTING"))
    assert "DMI" not in demand_line


# ── 3. thesis_book=None -> honest empty states, still byte-stable ────────────

def test_thesis_book_none_renders_honest_empty_states():
    out = render_report(_rich_sc(), None, _reg(), render_ts="fixed", thesis_book=None)
    assert "THE CALLS" in out
    assert "(no thesis book yet - runs after the first thesis cycle)" in out
    assert "WHY" in out
    assert "(no thesis book yet)" in out


def test_thesis_book_none_is_byte_stable_end_to_end():
    a = render_report(_rich_sc(), None, _reg(), render_ts="fixed", thesis_book=None)
    b = render_report(_rich_sc(), None, _reg(), render_ts="fixed", thesis_book=None)
    assert a == b


# ── 4. CLI loading: seeded+judged book -> THE CALLS content; absent -> empty state

def _run(*args: str):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True,
                          text=True, encoding="utf-8", env=env)


def _seed_and_judge_thesis_store(store: Path, tmp_path: Path) -> None:
    seed = _run("thesis", "--emit-prompt", "--findings", GOLDEN_FINDINGS,
                "--store", str(store), "--category", "chips.merchant-gpu",
                "--as-of", "2026-07-03")
    assert seed.returncode == 0, seed.stderr

    # Reuse the committed clean-answer fixture (5-1 flow), but flip one verdict off
    # "reaffirmed" so this cycle isn't the uniform-reaffirmed case — render_the_calls's
    # "Nothing changed this cycle" headline (by design) replaces the full three-line
    # block, including its "breaks if:" line, exactly when EVERY standing thesis
    # reaffirms; this scenario wants the full per-thesis block, so one verdict must
    # actually move.
    answer = json.loads(CLEAN_ANSWER.read_text("utf-8"))
    answer["judgments"][0]["verdict"] = "strengthened"
    answer_path = tmp_path / "answer-one-strengthened.json"
    answer_path.write_text(json.dumps(answer), "utf-8")

    applied = _run("thesis", "--recorded", str(answer_path),
                   "--findings", GOLDEN_FINDINGS, "--store", str(store),
                   "--category", "chips.merchant-gpu", "--as-of", "2026-07-03")
    assert applied.returncode == 0, applied.stderr


def test_cli_report_shows_the_calls_from_judged_thesis_book(tmp_path):
    store = tmp_path / "store"
    _seed_and_judge_thesis_store(store, tmp_path)

    result = _run("report", "--scorecard", POSTB_SCORECARD, "--store", str(store),
                  "--no-prior", "--render-ts", "2026-07-03T00:00:00Z")
    assert result.returncode == 0, result.stderr
    assert "● " in result.stdout
    assert "breaks if:" in result.stdout


def test_cli_report_without_theses_store_is_empty_state(tmp_path):
    store = tmp_path / "store"
    store.mkdir()

    result = _run("report", "--scorecard", POSTB_SCORECARD, "--store", str(store),
                  "--no-prior", "--render-ts", "t")
    assert result.returncode == 0, result.stderr
    assert "(no thesis book yet - runs after the first thesis cycle)" in result.stdout


# ── 5. byte-determinism with the full input set ───────────────────────────────

def test_byte_determinism_with_thesis_book_and_movement():
    sc = _rich_sc()
    book = _book()
    movement = _movement()
    a = render_report(sc, None, _reg(), render_ts="fixed", thesis_book=book, movement=movement)
    b = render_report(sc, None, _reg(), render_ts="fixed", thesis_book=book, movement=movement)
    assert a == b
