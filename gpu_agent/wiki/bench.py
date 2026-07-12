"""F25 benchmark helper: build a synthetic wiki store and time the hot ops.
Public-API only so it runs against both the pre- and post-optimization code."""
from __future__ import annotations
import time
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid: str) -> Finding:
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06-01",
        indicatorId="gpuSpotPrice", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="e", observedAt="2026-06-01", capturedAt="2026-06-01")


def build_synthetic(root, findings_root, *, pages: int, obs_per_page: int,
                    as_of: str = "2026-06-01") -> WikiStore:
    fs = FindingStore(findings_root)
    store = WikiStore(root, fs)
    for p in range(pages):
        pid = f"entity:e{p:04d}"
        store.create_page(pid, "entity", f"Title{p:04d}", as_of=as_of,
                          body=f"## Title{p:04d}\nbody for page {p}\n")
        for o in range(obs_per_page):
            fid = f"f-{p:04d}-{o:03d}"
            fs.append(_finding(fid))
            store.append_observation(pid, fid, as_of=as_of)
    return store


def time_ops(store, registry, horizons) -> dict:
    ids = [e.id for e in store.index()]
    out = {}
    t = time.perf_counter(); store.index(); out["index"] = time.perf_counter() - t
    t = time.perf_counter()
    for pid in ids:
        store.observations(pid)
    out["observations_all"] = time.perf_counter() - t
    t = time.perf_counter()
    health_report(store, as_of="2026-06-01", contradictions={}, horizons=horizons,
                  config=DEFAULT_LINT_CONFIG)
    out["health"] = time.perf_counter() - t
    return out
