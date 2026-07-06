"""eval-v2 (replicate baseline) unit tests — pure decision math over synthetic reports.
Spec: docs/superpowers/specs/2026-07-05-eval-v2-replicate-baseline-design.md."""
from __future__ import annotations
import json
import statistics
import pytest
from gpu_agent.evals.cases import EvalCase
from gpu_agent.evals.harness import (
    append_run_to_history, case_medians, compute_epsilon, pooled_epsilon, seam_quanta)

HASHES = {"extract": "a" * 64, "judge": "b" * 64, "thesis": "c" * 64}
DOC = {"id": "d1", "source": "s", "url": "http://x", "date": "2026-07-01",
       "tier": "primary", "entity": "NVDA", "content": "Blackwell shipments doubled."}

def _case(case_id, kind="positive", seam="extract"):
    return EvalCase.model_validate({
        "caseId": case_id, "seam": seam, "kind": kind, "source": "t",
        "input": {"doc": DOC, "asOf": "2026-07-03"},
        "recordedAnswer": json.dumps({"findings": []}),
        "checks": {"gateOutcome": "pass"}, "notes": "n",
    })

def test_seam_quanta_counts_positives_only():
    cases = [_case("e1"), _case("e2"), _case("e3", kind="negative"),
             _case("e4"), _case("e5")]
    assert seam_quanta(cases) == {"extract": 0.25}

def test_compute_epsilon_half_range():
    means = [{"extract": 6.75}, {"extract": 6.375}, {"extract": 6.5}]
    eps = compute_epsilon(means, {"extract": 0.125})
    assert eps["extract"] == pytest.approx(0.1875)

def test_compute_epsilon_quantum_floor_when_replicates_tie():
    means = [{"thesis": 6.0}, {"thesis": 6.0}, {"thesis": 6.0}]
    assert compute_epsilon(means, {"thesis": 0.5}) == {"thesis": 0.5}

def test_case_medians_positives_only_median_of_three():
    scores = [{"e1": 7, "e2": 4, "n1": 2}, {"e1": 5, "e2": 8, "n1": 0},
              {"e1": 6, "e2": 6, "n1": 1}]
    assert case_medians(scores, {"e1", "e2"}) == {"e1": 6, "e2": 6}


# --- F73c: pooled-dispersion epsilon that converges on real run noise ----------

def test_pooled_epsilon_uses_sample_stdev_over_quantum_floor():
    hist = {"extract": [6.5, 6.6, 6.4, 6.7, 6.3]}   # spread ~0.158 stdev
    eps = pooled_epsilon(hist, {"extract": 0.01})
    # 2 * sample stdev, above the tiny quantum floor
    assert eps["extract"] == pytest.approx(2 * 0.158113883, abs=1e-6)

def test_pooled_epsilon_quantum_floor_when_history_too_short():
    assert pooled_epsilon({"thesis": [6.0]}, {"thesis": 0.5}) == {"thesis": 0.5}

def test_append_run_grows_history_and_recomputes_epsilon():
    base = {"seamMeans": {"extract": 6.5}, "epsilon": {"extract": 0.25},
            "seamHistory": {"extract": [6.5, 6.6, 6.4]},
            "replicates": [{"seamMeans": {"extract": 6.5}}]}
    out = append_run_to_history(base, {"seamMeans": {"extract": 6.55}})
    assert out["seamHistory"]["extract"] == [6.5, 6.6, 6.4, 6.55]
    assert out["epsilon"]["extract"] > 0            # recomputed, not the stale 0.25 unless equal

def test_append_seeds_history_from_replicates_when_absent():
    base = {"seamMeans": {"extract": 6.5}, "epsilon": {"extract": 0.5},
            "replicates": [{"seamMeans": {"extract": 6.4}},
                           {"seamMeans": {"extract": 6.6}},
                           {"seamMeans": {"extract": 6.5}}]}
    out = append_run_to_history(base, {"seamMeans": {"extract": 6.5}})
    assert out["seamHistory"]["extract"] == [6.4, 6.6, 6.5, 6.5]


from gpu_agent.evals.harness import evaluate_v2

def _report(seam_means, scores, hashes=HASHES, calibration=None):
    return {"seamMeans": seam_means,
            "scores": {cid: {"total": t, "grades": {}} for cid, t in scores.items()},
            "calibration": calibration if calibration is not None else {},
            "promptHashes": hashes, "asOf": "2026-07-05"}

# baseline: mean 6.5, eps 0.25 -> bar 6.25, hard bar 6.0; medians e1=7, e2=6
BASE = {"schemaVersion": 2, "promptHashes": HASHES,
        "seamMeans": {"extract": 6.5}, "epsilon": {"extract": 0.25},
        "caseMedians": {"e1": 7, "e2": 6}}

def test_verdict_pass_on_bar_touch():
    v = evaluate_v2(BASE, [_report({"extract": 6.25}, {"e1": 7, "e2": 6})])
    assert (v["decision"], v["pass"]) == ("pass", True)

def test_verdict_marginal_within_one_epsilon_below_bar():
    v = evaluate_v2(BASE, [_report({"extract": 6.0}, {"e1": 7, "e2": 5})])
    assert v["decision"] == "marginal-fail"
    assert any("extract" in r for r in v["reasons"])

def test_verdict_hard_fail_below_two_epsilon():
    v = evaluate_v2(BASE, [_report({"extract": 5.875}, {"e1": 6, "e2": 6})])
    assert (v["decision"], v["pass"]) == ("hard-fail", False)

def test_crater_fails_at_median_minus_three_even_when_seam_passes():
    # e1 total 4 = median 7 - 3 -> crater (marginal band: within 1 beyond the line)
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 4, "e2": 8})])
    assert v["decision"] == "marginal-fail"
    assert v["craters"] == [{"caseId": "e1", "value": 4, "median": 7}]

def test_crater_hard_fails_at_median_minus_five():
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 2, "e2": 8})])
    assert v["decision"] == "hard-fail"

def test_two_run_mean_decides_after_marginal():
    r1 = _report({"extract": 6.0}, {"e1": 7, "e2": 5})
    r2 = _report({"extract": 6.5}, {"e1": 7, "e2": 6})   # mean 6.25 == bar -> pass
    assert evaluate_v2(BASE, [r1, r2])["decision"] == "pass"
    r3 = _report({"extract": 6.375}, {"e1": 7, "e2": 6})  # mean 6.1875 < bar -> fail
    assert evaluate_v2(BASE, [r1, r3])["decision"] == "fail"

def test_invalid_run_on_miscalibration_missing_seam_or_hash_mismatch():
    bad_cal = _report({"extract": 6.5}, {"e1": 7, "e2": 6},
                      calibration={"n1": {"score": 5, "max": 4, "ok": False}})
    assert evaluate_v2(BASE, [bad_cal])["decision"] == "invalid-run"
    no_seam = _report({}, {"e1": 7, "e2": 6})
    assert evaluate_v2(BASE, [no_seam])["decision"] == "invalid-run"
    other = _report({"extract": 6.5}, {"e1": 7, "e2": 6}, hashes={"extract": "z" * 64})
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 7, "e2": 6}), other])
    assert v["decision"] == "invalid-run"

def test_invalid_run_on_empty_reports():
    v = evaluate_v2(BASE, [])
    assert (v["decision"], v["pass"]) == ("invalid-run", False)

def test_invalid_run_when_baseline_case_missing_from_scores():
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 7})])   # e2 missing
    assert v["decision"] == "invalid-run"
    assert any("e2" in r for r in v["reasons"])


import pathlib
from gpu_agent.evals.harness import build_baseline_v2, load_baseline, rebaseline_v2

def _rep_full(extract_mean, e1, e2, hashes=HASHES):
    return _report({"extract": extract_mean}, {"e1": e1, "e2": e2, "n1": 0},
                   hashes=hashes,
                   calibration={"n1": {"score": 0, "max": 4, "ok": True}})

CASES3 = None  # built lazily: two positives e1/e2 + negative n1

def _cases3():
    global CASES3
    if CASES3 is None:
        CASES3 = [_case("e1"), _case("e2"), _case("n1", kind="negative")]
    return CASES3

def _write_runs(tmp_path, reports):
    dirs = []
    for i, rep in enumerate(reports):
        d = tmp_path / f"r{i + 1}"
        d.mkdir()
        (d / "report.json").write_text(json.dumps(rep), "utf-8")
        dirs.append(d)
    return dirs

def test_build_baseline_v2_shape():
    reports = [_rep_full(6.5, 7, 6), _rep_full(6.0, 6, 6), _rep_full(6.5, 8, 5)]
    b = build_baseline_v2(reports, ["r1", "r2", "r3"], _cases3(), None, "spot-checked")
    assert b["schemaVersion"] == 2
    assert b["seamMeans"]["extract"] == pytest.approx((6.5 + 6.0 + 6.5) / 3)
    # F73c: epsilon is now 2*sample-stdev of the replicate seam means (0.577), above the
    # 0.5 quantum floor — the pooled-dispersion band replaces the v1 half-range.
    assert b["epsilon"]["extract"] == pytest.approx(2 * statistics.stdev([6.5, 6.0, 6.5]))
    assert b["caseMedians"] == {"e1": 7, "e2": 6}
    assert [r["runDir"] for r in b["replicates"]] == ["r1", "r2", "r3"]
    assert b["provenance"]["humanReview"] == "spot-checked"

def test_build_baseline_v2_stores_quanta_and_history():
    reports = [_rep_full(6.5, 7, 6), _rep_full(6.0, 6, 6), _rep_full(6.5, 8, 5)]
    b = build_baseline_v2(reports, ["r1", "r2", "r3"], _cases3(), None, "spot-checked")
    assert b["quanta"]["extract"] == pytest.approx(0.5)      # 2 positives -> 1/2
    assert b["seamHistory"]["extract"] == [r["seamMeans"]["extract"] for r in reports]
    assert b["epsilon"]["extract"] == pytest.approx(pooled_epsilon(
        {"extract": b["seamHistory"]["extract"]}, {"extract": 0.5})["extract"])

def test_rebaseline_v2_bootstrap_writes(tmp_path):
    dirs = _write_runs(tmp_path, [_rep_full(6.5, 7, 6), _rep_full(6.0, 6, 6),
                                  _rep_full(6.5, 8, 5)])
    out = tmp_path / "baseline.json"
    rebaseline_v2(dirs, out, HASHES, _cases3())
    assert load_baseline(out)["schemaVersion"] == 2

def test_rebaseline_v2_refusals(tmp_path):
    good = [_rep_full(6.5, 7, 6), _rep_full(6.0, 6, 6), _rep_full(6.5, 8, 5)]
    out = tmp_path / "baseline.json"
    with pytest.raises(ValueError, match="exactly 3"):
        rebaseline_v2(_write_runs(tmp_path, good[:2]), out, HASHES, _cases3())
    mixed = [good[0], good[1], _rep_full(6.5, 8, 5, hashes={"extract": "z" * 64})]
    m2 = tmp_path / "m2"; m2.mkdir()
    with pytest.raises(ValueError, match="hash"):
        rebaseline_v2(_write_runs(m2, mixed), out, HASHES, _cases3())
    stale = tmp_path / "s"; stale.mkdir()
    with pytest.raises(ValueError, match="current"):
        rebaseline_v2(_write_runs(stale, good), out, {"extract": "z" * 64}, _cases3())
    dirty = [_rep_full(6.5, 7, 6), _rep_full(6.0, 6, 6),
             _report({"extract": 6.5}, {"e1": 8, "e2": 5, "n1": 5}, calibration={
                 "n1": {"score": 5, "max": 4, "ok": False}})]
    dd = tmp_path / "d"; dd.mkdir()
    with pytest.raises(ValueError, match="calibrat"):
        rebaseline_v2(_write_runs(dd, dirty), out, HASHES, _cases3())
    wide = [_rep_full(7.5, 8, 8), _rep_full(6.0, 6, 6), _rep_full(6.5, 7, 6)]
    wd = tmp_path / "w"; wd.mkdir()
    with pytest.raises(ValueError, match="dispersion"):
        rebaseline_v2(_write_runs(wd, wide), out, HASHES, _cases3())

def test_rebaseline_v2_governance(tmp_path):
    good = [_rep_full(6.5, 7, 6), _rep_full(6.0, 6, 6), _rep_full(6.5, 8, 5)]
    out = tmp_path / "baseline.json"
    rebaseline_v2(_write_runs(tmp_path, good), out, HASHES, _cases3())  # bootstrap
    # same hashes, existing v2 -> refused without force
    s2 = tmp_path / "s2"; s2.mkdir()
    with pytest.raises(ValueError, match="force"):
        rebaseline_v2(_write_runs(s2, good), out, HASHES, _cases3())
    # different hashes (prompt change) -> refused without a PASS verdict
    new_h = {"extract": "d" * 64, "judge": "b" * 64, "thesis": "c" * 64}
    new = [_rep_full(6.5, 7, 6, hashes=new_h), _rep_full(6.25, 7, 6, hashes=new_h),
           _rep_full(6.5, 6, 6, hashes=new_h)]
    n1 = tmp_path / "n1"; n1.mkdir()
    with pytest.raises(ValueError, match="verdict"):
        rebaseline_v2(_write_runs(n1, new), out, new_h, _cases3())
    n2 = tmp_path / "n2"; n2.mkdir()
    rebaseline_v2(_write_runs(n2, new), out, new_h, _cases3(),
                  verdict={"decision": "pass", "promptHashes": new_h})
    assert load_baseline(out)["promptHashes"] == new_h
    # v1 existing + same hashes -> migration path, allowed without force
    v1 = tmp_path / "v1.json"
    v1.write_text(json.dumps({"promptHashes": HASHES, "cases": {},
                              "seamMeans": {"extract": 6.5}, "provenance": {}}), "utf-8")
    m1 = tmp_path / "mig"; m1.mkdir()
    rebaseline_v2(_write_runs(m1, good), v1, HASHES, _cases3())
    assert load_baseline(v1)["schemaVersion"] == 2
