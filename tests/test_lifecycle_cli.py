import json
from gpu_agent.cli import main
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _seed_promotable(root):
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    def f(fid, sources, asOf, capturedAt):
        ev = [Evidence(source=s, url=f"http://{s}/x", date=asOf, excerpt="e", tier="secondary") for s in sources]
        return Finding(id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
                       impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                       value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
                       indicatorId="rpoBacklog", side="demand", polarityDemand=1, polaritySupply=0,
                       magnitude=2, entity="NVDA", observedAt=asOf, capturedAt=capturedAt, evidence=ev)
    store.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06")
    for fid, srcs, asof, cap in [("f1", ["sec"], "2026-06", "2026-06-01"),
                                 ("f2", ["reuters"], "2026-07", "2026-07-01")]:
        store.findings.append(f(fid, srcs, asof, cap))
        store.append_observation("entity:nvda", fid, as_of=asof)
    return store


def test_wiki_lifecycle_propose_prints_report(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_promotable(root)
    rc = main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert [c["pageId"] for c in report["promotions"]] == ["entity:nvda"]
    # propose did NOT mutate
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    assert store.get_page("entity:nvda").status == "provisional"


def test_wiki_lifecycle_apply_promotes(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_promotable(root)
    rc = main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07", "--apply"])
    assert rc == 0
    assert "promoted 1" in capsys.readouterr().out
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    assert store.get_page("entity:nvda").status == "registered"


def test_wiki_lifecycle_apply_idempotent(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_promotable(root)
    main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07", "--apply"])
    capsys.readouterr()
    main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-08", "--apply"])
    assert "promoted 0" in capsys.readouterr().out  # already registered


def test_wiki_lifecycle_writes_report_file(tmp_path):
    root = tmp_path / "store"
    _seed_promotable(root)
    out = tmp_path / "lifecycle.json"
    rc = main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07", "--report", str(out)])
    assert rc == 0
    report = json.loads(out.read_text("utf-8"))
    assert report["provisionalConsidered"] == 1
