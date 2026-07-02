"""CLI `thesis` subcommand (Task 7): emit -> recorded, mirroring extract/judge's pattern,
plus the judge --store memory-threading seam it shares. Subprocess pattern per
tests/test_cli_persona.py / tests/test_cli_emit_prompt.py -- exercises the real CLI entry
point end to end, no monkeypatching.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PY = sys.executable

SEED_IDS = [
    "nvda-demand-durability",
    "supply-constraint-binding",
    "amd-credible-second-source",
    "custom-asic-substitution",
    "pricing-power-persistence",
    "export-control-exposure",
]

CLEAN_ANSWER = Path("tests/fixtures/thesis-answer-clean.json")


def _run(*args):
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True, text=True)


def _book_path(store: Path, category: str = "chips.merchant-gpu") -> Path:
    return store / "theses" / category / "book.json"


def _history_path(store: Path, category: str = "chips.merchant-gpu") -> Path:
    return store / "theses" / category / "history.jsonl"


# --- 1. --emit-prompt seeds the store (first run) and emits system/schema/user ------------


def test_thesis_emit_prompt_seeds_and_emits_canonical_bundle(tmp_path):
    store = tmp_path / "store"
    out = _run("thesis", "--emit-prompt", "--findings", "fixtures/golden/findings.json",
               "--store", str(store), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07-03")

    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert set(bundle) == {"system", "schema", "user"}
    assert bundle["schema"]["title"] == "ThesisAnswer"
    assert "<book>" in bundle["user"]
    for thesis_id in SEED_IDS:
        assert thesis_id in bundle["user"], thesis_id

    assert "seeded 6 theses" in out.stderr

    assert _book_path(store).exists()


# --- 2. --recorded with a clean answer applies + writes ------------------------------------


def test_thesis_recorded_clean_answer_applies_and_updates_book(tmp_path):
    store = tmp_path / "store"
    out = _run("thesis", "--recorded", str(CLEAN_ANSWER),
               "--findings", "fixtures/golden/findings.json",
               "--store", str(store), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07-03")

    assert out.returncode == 0, out.stderr

    book = json.loads(_book_path(store).read_text("utf-8"))
    assert len(book["entries"]) == 6
    for entry in book["entries"]:
        assert entry["lastJudgedAsOf"] == "2026-07-03", entry

    history_lines = _history_path(store).read_text("utf-8").splitlines()
    assert len(history_lines) > 1  # seed record + at least one judgment record

    # one summary line per thesis: "<id>: <verdict> applied=<bool> conviction=<level>"
    for thesis_id in SEED_IDS:
        assert any(
            line.startswith(f"{thesis_id}: reaffirmed applied=") for line in out.stdout.splitlines()
        ), out.stdout


# --- 3. --recorded missing a judgment -> gate rejects, book byte-unchanged -----------------


def test_thesis_recorded_missing_judgment_rejected_book_untouched(tmp_path):
    store = tmp_path / "store"
    seed_out = _run("thesis", "--emit-prompt", "--findings", "fixtures/golden/findings.json",
                     "--store", str(store), "--category", "chips.merchant-gpu",
                     "--as-of", "2026-07-03")
    assert seed_out.returncode == 0, seed_out.stderr
    book_path = _book_path(store)
    before = book_path.read_bytes()

    answer = json.loads(CLEAN_ANSWER.read_text("utf-8"))
    answer["judgments"] = [
        j for j in answer["judgments"] if j["thesisId"] != "export-control-exposure"
    ]
    bad_answer = tmp_path / "bad-answer.json"
    bad_answer.write_text(json.dumps(answer), "utf-8")

    out = _run("thesis", "--recorded", str(bad_answer),
               "--findings", "fixtures/golden/findings.json",
               "--store", str(store), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07-10")

    assert out.returncode == 1, out.stdout
    assert "export-control-exposure" in out.stderr
    assert book_path.read_bytes() == before


# --- 4. judge --emit-prompt --store threads prior-cycle MEMORY into the user prompt --------


def _finding_json(fid: str, as_of: str) -> dict:
    return {
        "id": fid, "statement": "s", "kind": "observed", "trend": "flat", "why": "w",
        "impact": {"targets": ["chips.merchant-gpu"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": as_of, "excerpt": "e", "tier": "primary"}],
        "confidence": {"level": "medium", "basis": "b"}, "asOf": as_of,
        "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
        "magnitude": 2, "entity": "NVDA", "observedAt": as_of,
        "capturedAt": f"{as_of}-01T00:00:00Z",
    }


def test_judge_emit_prompt_threads_memory_when_store_has_a_prior_scorecard(tmp_path):
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps([_finding_json("f-1", "2026-08")]), "utf-8")

    store_with_prior = tmp_path / "store-prior"
    cat_dir = store_with_prior / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v1.json").write_text(
        Path("fixtures/report/prior-chain/2026-06-v1.json").read_text("utf-8"), "utf-8"
    )

    out = _run("judge", "--emit-prompt", "--findings", str(findings_path),
               "--category", "chips.merchant-gpu", "--store", str(store_with_prior))
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "MEMORY (" in bundle["user"]


def test_judge_emit_prompt_empty_store_is_byte_identical_to_legacy_prompt(tmp_path):
    # The default --store ("store", the checked-out cycle history) has no scorecard labeled
    # strictly before 2026-06 for this category (everything on disk is >= 2026-06), so it must
    # contribute nothing -- output byte-identical to an explicitly empty --store, which is in
    # turn byte-identical to the pre-memory-threading prompt (no MEMORY block at all).
    default_store = _run("judge", "--emit-prompt", "--findings", "fixtures/golden/findings.json",
                         "--category", "chips.merchant-gpu")
    empty_store = _run("judge", "--emit-prompt", "--findings", "fixtures/golden/findings.json",
                       "--category", "chips.merchant-gpu", "--store", str(tmp_path / "nostore"))

    assert default_store.returncode == 0, default_store.stderr
    assert empty_store.returncode == 0, empty_store.stderr
    assert "MEMORY (" not in json.loads(default_store.stdout)["user"]
    assert "MEMORY (" not in json.loads(empty_store.stdout)["user"]
    assert default_store.stdout == empty_store.stdout


# --- 5. neither --emit-prompt nor --recorded -> exit 2 --------------------------------------


def test_thesis_neither_flag_exits_2(tmp_path):
    out = _run("thesis", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path / "store"), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07-03")
    assert out.returncode == 2, out.stdout
