# tests/test_cli_corpus.py
import json
import subprocess
import sys

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore


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


def _write_fresh(tmp_path, findings):
    p = tmp_path / "fresh.json"
    p.write_text(json.dumps([f.model_dump() for f in findings], indent=2), "utf-8")
    return p


def test_store_only_mode_prints_coverage(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02"), "2026-07-02")
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--report", str(tmp_path / "cov.json"))
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("STORE COVERAGE")
    assert "NVDA designWins" in out.stdout
    report = json.loads((tmp_path / "cov.json").read_text("utf-8"))
    assert report["storeIncluded"] == ["store-1"]


def test_store_only_mode_empty_store(tmp_path):
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07")
    assert out.returncode == 0, out.stderr
    assert "no store coverage" in out.stdout


def test_fresh_requires_out_merged(tmp_path):
    fresh = _write_fresh(tmp_path, [_f("fresh-1")])
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--fresh", str(fresh))
    assert out.returncode == 2
    assert "--out-merged" in out.stderr


def test_assemble_mode_writes_artifacts_and_summary(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", entity="AMD", as_of="2026-07-02"), "2026-07-02")
    fresh = _write_fresh(tmp_path, [_f("fresh-1", indicatorId="rpoBacklog",
                                       as_of="2026-07", entity="NVDA")])
    merged_p = tmp_path / "merged.json"
    deduped_p = tmp_path / "deduped.json"
    report_p = tmp_path / "report.json"
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--fresh", str(fresh),
               "--out-merged", str(merged_p), "--out-deduped-fresh", str(deduped_p),
               "--report", str(report_p))
    assert out.returncode == 0, out.stderr
    merged = json.loads(merged_p.read_text("utf-8"))
    assert [f["id"] for f in merged] == ["store-1", "fresh-1"]
    deduped = json.loads(deduped_p.read_text("utf-8"))
    assert [f["id"] for f in deduped] == ["fresh-1"]
    assert "store 1 aged (0 faded), fresh new 1 update 0 duplicate 0 -> merged 2" \
        in out.stdout


def test_drops_and_skips_hit_stderr(tmp_path):
    store = _store(tmp_path)
    prior = _f("store-1", as_of="2026-07-02")
    _seed(store, prior, "2026-07-02")
    _seed(store, _f("theirs-1", entity="OPENAI", as_of="2026-07-02"), "2026-07-02",
          category="models.frontier-closed")
    dup = _f("fresh-dup", as_of="2026-07").model_copy(
        update={"statement": prior.statement})
    fresh = _write_fresh(tmp_path, [dup])
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--fresh", str(fresh),
               "--out-merged", str(tmp_path / "m.json"))
    assert out.returncode == 0, out.stderr
    assert "SKIPPED-PAGE entity:openai: category=models.frontier-closed" in out.stderr
    assert "DROPPED-DUPLICATE fresh-dup" in out.stderr


def test_bad_as_of_label_exits_1(tmp_path):
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026/07")
    assert out.returncode == 1
    assert "invalid asOf label" in out.stderr
