import json
import subprocess
import sys

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

CAPTURED = "2026-06-12T00:00:00Z"


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _extract_fresh(tmp_path):
    out_p = tmp_path / "findings.json"
    r = _run("extract", "--recorded", "fixtures/recorded/extract-nvda.json",
             "--docs", "fixtures/raw", "--as-of", "2026-06",
             "--captured-at", CAPTURED, "--out", str(out_p))
    assert r.returncode == 0, r.stderr
    return out_p


def _seed_store(tmp_path):
    """One in-window store finding on a dimension-less, non-scoring indicator
    (flopsPerDollar): lands in scorecard.findings without touching anchors,
    citation groups, or DMI/SMI — the recorded judge fixture replays unchanged."""
    store = _store(tmp_path / "store")
    f = _f("seeded-store-1", entity="SEEDCO", indicatorId="flopsPerDollar",
           as_of="2026-05-20", observedAt="2026-05-20")
    _seed(store, f, "2026-05-20")
    return f


def test_pipeline_without_corpus_flags_unchanged(tmp_path):
    _seed_store(tmp_path)   # present on disk, must NOT be read without the flags
    r = _run("pipeline", "--docs", "fixtures/raw",
             "--assignment", "fixtures/asg.chips.merchant-gpu.json",
             "--as-of", "2026-06", "--captured-at", CAPTURED,
             "--recorded-extract", "fixtures/recorded/extract-nvda.json",
             "--recorded-judge", "fixtures/recorded/judge-nvda.json",
             "--no-voice-lint", "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert "corpus:" not in r.stderr
    sc = json.loads(next((tmp_path / "out" / "chips.merchant-gpu").glob("*.json"))
                    .read_text("utf-8"))
    assert all(f["id"] != "seeded-store-1" for f in sc["findings"])


def test_pipeline_corpus_merges_store_finding_and_matches_corpus_cli(tmp_path):
    fresh_p = _extract_fresh(tmp_path)
    _seed_store(tmp_path)
    store_root = str(tmp_path / "store")

    # the corpus CLI's merged file (what judge --emit-prompt would consume)
    merged_p = tmp_path / "merged.json"
    r = _run("corpus", "--store", store_root, "--category", "chips.merchant-gpu",
             "--as-of", "2026-06", "--fresh", str(fresh_p),
             "--out-merged", str(merged_p))
    assert r.returncode == 0, r.stderr
    merged_ids = [f["id"] for f in json.loads(merged_p.read_text("utf-8"))]
    assert "seeded-store-1" in merged_ids

    # pipeline with the corpus flags: scorecard findings == the corpus CLI's merge
    report_p = tmp_path / "corpus-report.json"
    r = _run("pipeline", "--docs", "fixtures/raw",
             "--assignment", "fixtures/asg.chips.merchant-gpu.json",
             "--as-of", "2026-06", "--captured-at", CAPTURED,
             "--recorded-extract", "fixtures/recorded/extract-nvda.json",
             "--recorded-judge", "fixtures/recorded/judge-nvda.json",
             "--no-voice-lint",
             "--corpus-store", store_root, "--corpus-report", str(report_p),
             "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert "corpus: store 1 in-window" in r.stderr
    sc = json.loads(next((tmp_path / "out" / "chips.merchant-gpu").glob("*.json"))
                    .read_text("utf-8"))
    assert [f["id"] for f in sc["findings"]] == merged_ids       # the equality pin
    report = json.loads(report_p.read_text("utf-8"))
    assert report["storeIncluded"] == ["seeded-store-1"]


def test_pipeline_corpus_error_fails_loud(tmp_path):
    (tmp_path / "store" / "wiki").mkdir(parents=True)
    # 2026-13 passes F56's --as-of shape validator (YYYY-MM) but fails the corpus
    # layer's month-range check, so the corpus error path is what fails loud here.
    # (A slash shape like 2026/06 would now be rejected at argparse by F56 → rc 2.)
    r = _run("pipeline", "--docs", "fixtures/raw",
             "--assignment", "fixtures/asg.chips.merchant-gpu.json",
             "--as-of", "2026-13", "--captured-at", CAPTURED,
             "--recorded-extract", "fixtures/recorded/extract-nvda.json",
             "--recorded-judge", "fixtures/recorded/judge-nvda.json",
             "--no-voice-lint",
             "--corpus-store", str(tmp_path / "store"),
             "--out", str(tmp_path / "out"))
    assert r.returncode == 1
    assert "corpus error" in r.stderr


def test_store_finding_citable_in_scorecard_and_report():
    """Spec e2e: a store-vintage finding is citable — the frozen gate validates a
    rating citing it and the rendered report's citation map resolves the id."""
    from gpu_agent.assignment import load_assignment
    from gpu_agent.pipeline import build_scorecard
    from gpu_agent.registry.horizon import IndicatorHorizons
    from gpu_agent.registry.indicators import IndicatorRegistry
    from gpu_agent.report import render_report
    from gpu_agent.schema.scorecard import DimensionRating

    registry = IndicatorRegistry.load("registry/indicators.json")
    horizons = IndicatorHorizons.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    # designWins: side structural (matches the factory), dimension competitiveStructure
    store_f = _f("store-cited-1", indicatorId="designWins", as_of="2026-05-20",
                 observedAt="2026-05-20")
    fresh_f = _f("fresh-1", entity="AMD")
    merged = [store_f, fresh_f]
    ratings = {"competitiveStructure": DimensionRating(
        rating="Mixed", direction="steady", findingIds=["store-cited-1"],
        rationale="Cites the store-vintage finding.",
        confidence=Confidence(level="medium", basis="test"))}
    sc = build_scorecard(merged, ratings, {"competitiveStructure": 0.0}, a,
                         "n", Confidence(level="medium", basis="b"), registry,
                         horizons=horizons)
    assert "store-cited-1" in sc.dimensionRatings["competitiveStructure"].findingIds
    text = render_report(sc, None, registry, horizons=horizons,
                         render_ts="2026-07-04T00:00:00Z")
    assert "store-cited-1" in text   # the appendix CITATION MAP lists every finding
