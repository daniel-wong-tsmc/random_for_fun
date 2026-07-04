"""F63: the evidence-sufficiency gate wired at `judge --recorded` (Task 6). Consumes
Task 5's pure `check_sufficiency` (tests/test_sufficiency.py) via the SAME memory
source the emitted judge prompt carries -- build_memory_bundle(args.store, ...)
(F5 precedent, see tests/test_memory_bundle.py for the prior-scorecard seeding idiom).

Findings/recorded-answer plumbing follows tests/test_judge_voice_lint.py (the sibling
F67 CLI gate at the same seam) and CLI-invocation style follows
tests/test_cli_pipeline_corpus.py's subprocess `_run` helper.
"""
import json
import subprocess
import sys

CATEGORY = "chips.merchant-gpu"

GOOD_NARRATIVE = ("Demand is strong because hyperscaler orders exceed packaging output. "
                  "The crux is whether CoWoS capacity doubles by Q4. "
                  "Watch TSMC lead times first.")


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _finding(fid: str, tier: str) -> dict:
    # Same shape as test_judge_voice_lint.py's _clean_finding: indicatorId D2 maps to the
    # momentum dimension (registry/indicators.json), polarityDemand=1/magnitude=2 gives a
    # positive anchor consistent with BOTH "Strong" and "Very strong" (gate._POSITIVE).
    return {"id": fid, "statement": "s", "kind": "observed", "trend": "rising", "why": "w",
            "impact": {"targets": ["t"], "direction": "positive", "mechanism": "m"},
            "evidence": [{"source": "S", "url": "https://reuters.com/x", "date": "2026-07-01",
                          "excerpt": "e", "tier": tier}],
            "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-07",
            "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
            "magnitude": 2, "entity": "E", "observedAt": "2026-07-01",
            "capturedAt": "2026-07-04T00:00:00Z"}


def _findings_file(tmp_path, tier: str):
    fid = "doc-nvda-1"
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([_finding(fid, tier)]), "utf-8")
    return p, fid


def _judgment(fid: str) -> dict:
    return {"dimensions": {"momentum": {"rating": "Very strong", "direction": "improving",
             "findingIds": [fid], "rationale": "Orders accelerated further."}},
            "categoryStatus": {"rating": "Very strong", "direction": "improving",
                               "bottleneck": "momentum", "reason": "Orders accelerated."},
            "narrative": GOOD_NARRATIVE}


def _recorded_file(tmp_path, fid: str):
    p = tmp_path / "rec.json"
    p.write_text(json.dumps([json.dumps(_judgment(fid))]), "utf-8")
    return p


def _prior_scorecard() -> dict:
    """A prior cycle scorecard whose momentum rating is "Strong" -- the memory-bundle
    seeding idiom from tests/test_memory_bundle.py (a bare <asOf>-v1.json under
    <store>/<category>/), minimal enough for report.load_scorecard/Scorecard."""
    return {
        "categoryId": CATEGORY,
        "asOf": "2026-06",
        "demandSupply": {"dmiContribution": 0.1, "smiContribution": 0.05},
        "narrative": "prior cycle scorecard",
        "confidence": {"level": "medium", "basis": "prior"},
        "dimensionRatings": {
            "momentum": {
                "rating": "Strong", "direction": "steady",
                "confidence": {"level": "medium", "basis": "prior"},
                "findingIds": ["prior-1"], "rationale": "prior rationale",
            }
        },
    }


def _seed_prior_store(tmp_path):
    store = tmp_path / "store"
    cat_dir = store / CATEGORY
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v1.json").write_text(json.dumps(_prior_scorecard()), "utf-8")
    return store


def _judge_args(tmp_path, findings_p, recorded_p, store, *extra):
    return ("judge", "--findings", str(findings_p), "--category", CATEGORY,
            "--samples", "1", "--recorded", str(recorded_p),
            "--out", str(tmp_path / "jdg"), "--store", str(store), *extra)


def test_judge_recorded_rejects_undersourced_rating_change(tmp_path):
    store = _seed_prior_store(tmp_path)
    findings_p, fid = _findings_file(tmp_path, "secondary")   # single secondary evidence item
    rec = _recorded_file(tmp_path, fid)
    out = _run(*_judge_args(tmp_path, findings_p, rec, store))
    assert out.returncode == 1, out.stderr
    assert ("sufficiency: sample 1: momentum: rating changed Strong->Very strong"
            in out.stderr)


def test_judge_recorded_passes_with_primary_citation(tmp_path):
    store = _seed_prior_store(tmp_path)
    findings_p, fid = _findings_file(tmp_path, "primary")   # same setup, primary evidence
    rec = _recorded_file(tmp_path, fid)
    out = _run(*_judge_args(tmp_path, findings_p, rec, store))
    assert out.returncode == 0, out.stderr


def test_no_sufficiency_flag_skips_gate(tmp_path):
    store = _seed_prior_store(tmp_path)
    findings_p, fid = _findings_file(tmp_path, "secondary")   # same failing setup as test 1
    rec = _recorded_file(tmp_path, fid)
    out = _run(*_judge_args(tmp_path, findings_p, rec, store, "--no-sufficiency"))
    assert out.returncode == 0, out.stderr
    assert "sufficiency:" not in out.stderr


def test_judge_recorded_without_prior_scorecard_is_inert(tmp_path):
    store = tmp_path / "empty-store"   # no prior scorecard at all -> memory is None
    findings_p, fid = _findings_file(tmp_path, "secondary")   # same undersourced citation
    rec = _recorded_file(tmp_path, fid)
    out = _run(*_judge_args(tmp_path, findings_p, rec, store))
    assert out.returncode == 0, out.stderr
