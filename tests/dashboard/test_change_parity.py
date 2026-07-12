# tests/dashboard/test_change_parity.py
#
# F78 Task 11 — dashboard parity: build_model must carry the SAME alert/what-changed/
# banded-tile story as the text brief, sourced from the same change-engine calls
# (never re-derived). See gpu_agent/dashboard/build.py and render.py.
#
# Adaptation from the task brief's sketch: build_model's `store_dir` is the dashboard's
# existing, established convention — the category's own flat scorecard directory (e.g.
# "store/chips.merchant-gpu", the real CLI default in gpu_agent/dashboard/build.py::main
# and docs/superpowers/plans/2026-07-06-merchant-gpu-dashboard.md) — NOT the store ROOT
# that change.py/thesis.py/cli.py expect (e.g. "store", holding theses/<category>/ and
# <category>/ side by side, confirmed on disk under store/). Both conventions are real
# and frozen (test_scorecards.py and test_build_e2e.py pin the flat-dir convention for
# load_scorecards; cli.py/change.py pin the store-root convention elsewhere), so
# build_model derives the store root internally as store_dir.parent. This test therefore
# writes scorecards under store/chips.merchant-gpu/ and passes that flat directory (not
# its parent) as store_dir — matching real usage. Second adaptation: build_model returns
# (model, summary), not the model alone (brief's sketch omitted the tuple) — unpacked below.
from __future__ import annotations
from pathlib import Path
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Confidence
from gpu_agent.dashboard.build import build_model
from gpu_agent.dashboard.render import render_html


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(r, d="steady"):
    return DimensionRating(rating=r, direction=d, confidence=_conf(), findingIds=[], rationale="x")


def _write(store, as_of, dmi, smi, momentum="Strong"):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   dimensionRatings={"momentum": _dim(momentum)},
                   demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
                   narrative="n", confidence=_conf())
    (cat / f"{as_of}-v1.json").write_text(sc.model_dump_json(), "utf-8")


def test_model_carries_alert_bands_and_what_changed(tmp_path):
    store = tmp_path / "store"
    _write(store, "2026-07-07", 0.10, 0.10)
    _write(store, "2026-07-08", 0.10, 0.10, momentum="Very strong")
    m, _ = build_model("chips.merchant-gpu", store / "chips.merchant-gpu", tmp_path, None, "fixed")
    assert m["alert"]["color"] in ("green", "yellow", "orange", "red")
    assert m["alert"]["prior"] in (None, "green", "yellow", "orange", "red")
    # tiles carry the banded words, raw value stays only in the sub-label
    assert any("FIRM" in t["band"] for t in m["tiles"])
    assert all("band" in t for t in m["tiles"])
    # three horizons, exec-plain phrases
    phrases = [w["phrase"] for w in m["what_changed"]]
    assert phrases == ["Since yesterday", "Since last week", "Since last month"]


def test_html_renders_alert_and_what_changed_above_top_signals(tmp_path):
    store = tmp_path / "store"
    _write(store, "2026-07-07", 0.10, 0.10)
    _write(store, "2026-07-08", 0.10, 0.10)
    m, _ = build_model("chips.merchant-gpu", store / "chips.merchant-gpu", tmp_path, None, "fixed")
    html = render_html(m)
    assert 'id="what-changed"' in html
    assert html.index('id="what-changed"') < html.index('id="top-signals"')
    assert m["alert"]["color"].upper() in html


def test_single_run_store_is_first_run_safe(tmp_path):
    store = tmp_path / "store"
    _write(store, "2026-07-08", 0.10, 0.10)
    m, _ = build_model("chips.merchant-gpu", store / "chips.merchant-gpu", tmp_path, None, "fixed")
    assert m["alert"]["prior"] is None
    assert m["what_changed"][0]["text"].startswith("no run yet")
