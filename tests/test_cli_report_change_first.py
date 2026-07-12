# tests/test_cli_report_change_first.py
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Confidence

PY = sys.executable


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(r, d="steady"):
    return DimensionRating(rating=r, direction=d, confidence=_conf(), findingIds=[], rationale="x")


def _write(store, as_of, version, momentum_rating):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   dimensionRatings={"momentum": _dim(momentum_rating, "improving")},
                   demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                   narrative="n", confidence=_conf())
    p = cat / f"{as_of}-v{version}.json"
    p.write_text(sc.model_dump_json(), "utf-8")
    return p


def _run(*args):
    env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True,
                          text=True, encoding="utf-8", env=env)


def test_cli_change_first_emits_what_changed(tmp_path):
    store = tmp_path / "store"
    _write(store, "2026-07-07", 1, "Strong")
    cur = _write(store, "2026-07-08", 1, "Very strong")
    r = _run("report", "--scorecard", str(cur), "--store", str(store),
             "--change-first", "--render-ts", "fixed")
    assert r.returncode == 0, r.stderr
    assert "WHAT CHANGED" in r.stdout
    assert "QUICK GLANCE" in r.stdout
    assert "Since yesterday" in r.stdout
    # AMENDED 2026-07-11: the exec top band leads (nothing ladder-relevant moved -> GREEN)
    assert "MERCHANT GPU — DAILY — 2026-07-08" in r.stdout
    assert "● GREEN (was GREEN)" in r.stdout


def test_cli_without_flag_is_legacy(tmp_path):
    store = tmp_path / "store"
    cur = _write(store, "2026-07-08", 1, "Very strong")
    r = _run("report", "--scorecard", str(cur), "--store", str(store),
             "--no-prior", "--render-ts", "fixed")
    assert r.returncode == 0, r.stderr
    assert "WHAT CHANGED" not in r.stdout
