#!/usr/bin/env python
"""Contract v1.4 shadow-run — gate-behavior blast radius, NO store writes (spec §5).

Quantifies what the v1.4 gate deltas would change over the ALREADY-STORED series, without
re-gating or mutating anything (charter Part 33: originals immutable). Two questions:

  F72 (publisher distinctness): for every stored finding AND every stored dimension rating,
  the distinct-publisher count OLD (raw netloc, publisher_key) vs NEW (collapsed_publisher_set
  = syndicator registry + exact-hash near-dup). A "flip" is a corroboration verdict that
  changes: a finding that cleared gate F2e's high-confidence secondary-only bar (>=N distinct
  publishers) only because syndication inflated the count, or a dimension whose >=N corroboration
  crossed to <N. These are the findings that RELIED on the syndication hole.

  F71 (anchor vs sufficiency precedence): across consecutive stored versions of one cycle
  series, a dimension whose rating CHANGED, whose PRIOR rating is illegal under the current
  measured anchor (anchor-FORCED move), and whose current citations are under-sourced (no
  primary, <N collapsed publishers). OLD: deadlock -> shipped under a whole-run --no-sufficiency
  bypass. NEW: resolves via the anchor-forced-move exemption (stamped, no bypass).

Run from the repo root:  ../../.venv/Scripts/python scripts/shadow_run_v14.py
"""
from __future__ import annotations
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gpu_agent.report import load_scorecard
from gpu_agent.config import min_distinct_publishers
from gpu_agent.publisher import publisher_key, distinct_publisher_count
from gpu_agent.gate import _rating_consistent_with_anchor

STORE_GLOB = "store/chips.merchant-gpu/*.json"


def _raw_count(evidence) -> int:
    return len({publisher_key(e) for e in evidence})


def _load_scorecards():
    cards = []
    for fp in sorted(glob.glob(STORE_GLOB)):
        name = pathlib.Path(fp).name
        if name.startswith("dedup-"):
            continue   # dedup reports are not scorecards
        try:
            cards.append((name, load_scorecard(pathlib.Path(fp))))
        except Exception as e:   # noqa: BLE001 — a non-scorecard file just isn't one
            print(f"  (skip {name}: {e})")
    return cards


def _version(name: str) -> tuple:
    # "2026-07-v3.json" -> ("2026-07", 3); "2026-07-06-v1.json" -> ("2026-07-06", 1)
    stem = name[:-5]
    head, _, v = stem.rpartition("-v")
    try:
        return (head, int(v))
    except ValueError:
        return (stem, 0)


def f72_shadow(cards) -> None:
    n = min_distinct_publishers()
    print(f"\n== F72 — publisher-distinctness collapse (bar N={n}) ==")
    finding_total = finding_collapsed = 0
    dim_total = dim_collapsed = 0
    flips = []        # verdict-changing rows (crossed the N bar)
    near_misses = []  # count changed by the collapse but stayed the same side of the bar
    for name, sc in cards:
        by_id = {f.id: f for f in sc.findings}
        for f in sc.findings:
            finding_total += 1
            raw, new = _raw_count(f.evidence), distinct_publisher_count(f.evidence)
            if raw != new:
                finding_collapsed += 1
                near_misses.append((name, f"finding {f.id}", raw, new))
            all_secondary = bool(f.evidence) and all(e.tier == "secondary" for e in f.evidence)
            if all_secondary and f.confidence.level == "high" and raw >= n and new < n:
                flips.append((name, f"finding {f.id}", "F2e high-conf secondary-only",
                              raw, new))
        for dim, r in sc.dimensionRatings.items():
            evs = [e for fid in r.findingIds if fid in by_id for e in by_id[fid].evidence]
            if not evs:
                continue
            dim_total += 1
            raw, new = _raw_count(evs), distinct_publisher_count(evs)
            if raw != new:
                dim_collapsed += 1
                near_misses.append((name, f"dimension {dim}", raw, new))
            any_primary = any(e.tier == "primary" for e in evs)
            if not any_primary and raw >= n and new < n:
                flips.append((name, f"dimension {dim}", "corroboration >=N -> <N",
                              raw, new))
    print(f"  stored findings scanned:        {finding_total}  "
          f"(count changed by collapse: {finding_collapsed})")
    print(f"  stored dimension ratings scanned:{dim_total:>4}  "
          f"(count changed by collapse: {dim_collapsed})")
    if flips:
        print(f"  VERDICT FLIPS (relied on the hole): {len(flips)}")
        print(f"  {'scorecard':<22} {'subject':<34} {'why':<32} old->new")
        for name, subj, why, raw, new in flips:
            print(f"  {name:<22} {subj:<34} {why:<32} {raw}->{new}")
    else:
        print("  VERDICT FLIPS (relied on the hole): 0  "
              "— no stored finding/dimension crossed the corroboration bar via syndication")
    if near_misses:
        print(f"  collapse-affected but NON-flipping counts ({len(near_misses)}):")
        for name, subj, raw, new in near_misses:
            print(f"    {name:<22} {subj:<34} {raw}->{new}  (same side of N={n})")


def f71_shadow(cards) -> None:
    n = min_distinct_publishers()
    print(f"\n== F71 — anchor-forced-move exemption (would-have-deadlocked, N={n}) ==")
    by_asof: dict[str, list] = {}
    for name, sc in cards:
        head, ver = _version(name)
        by_asof.setdefault(head, []).append((ver, name, sc))
    forced = []
    for head, series in sorted(by_asof.items()):
        series.sort(key=lambda t: t[0])
        for (pv, pname, prior), (cv, cname, cur) in zip(series, series[1:]):
            anchors = cur.demandSupply.anchors or {}
            by_id = {f.id: f for f in cur.findings}
            for dim, r in cur.dimensionRatings.items():
                pr = prior.dimensionRatings.get(dim)
                a = anchors.get(dim)
                if pr is None or a is None or pr.rating == r.rating:
                    continue
                # anchor-forced: prior rating illegal under the current anchor, new rating legal
                if _rating_consistent_with_anchor(pr.rating, a):
                    continue
                if not _rating_consistent_with_anchor(r.rating, a):
                    continue
                evs = [e for fid in r.findingIds if fid in by_id for e in by_id[fid].evidence]
                any_primary = any(e.tier == "primary" for e in evs)
                collapsed = distinct_publisher_count(evs)
                under_sourced = not any_primary and collapsed < n
                if under_sourced:
                    forced.append((cname, dim, pr.rating, r.rating, a, collapsed))
    if forced:
        print(f"  anchor-forced under-sourced moves (structural pattern): {len(forced)}")
        print(f"  {'scorecard':<22} {'dim':<18} move          anchor  collapsedPubs")
        for cname, dim, prat, crat, a, collapsed in forced:
            print(f"  {cname:<22} {dim:<18} {prat}->{crat:<8} {a:+.2f}   {collapsed}")
        print("  Under v1.4 each of these resolves via the exemption (stamped 'anchor-bounded")
        print("  on thin evidence', no bypass) instead of deadlocking.")
        print("  HONESTY CAVEAT: these are 2026-06 cycles (and their v1.2 replays v7-v12) — the")
        print("  F63 sufficiency gate that TURNS such a move into a deadlock did not exist until")
        print("  contract v1.3 (2026-07), so none of these actually deadlocked at the time. They")
        print("  document the structural pattern the v1.4 exemption now handles cleanly.")
    else:
        print("  anchor-forced under-sourced moves across consecutive stored versions: 0 "
              "(computable series only)")
        print("  NOTE: the one recorded F71 firing (2026-07 v3 monthly, moat Weak->Mixed at "
              "+0.50) lives in the cycle-log gate record at git 99ca522, not reconstructable "
              "from the immutable scorecard series alone (the shipped v3 moat is the "
              "post-resolution 'Mixed', capped medium).")


def main() -> int:
    print("Contract v1.4 shadow-run (NO store writes) — store/chips.merchant-gpu/*.json")
    cards = _load_scorecards()
    print(f"scorecards loaded: {len(cards)}")
    f72_shadow(cards)
    f71_shadow(cards)
    print("\n(Read-only: this script writes nothing. Originals stay byte-unchanged — Part 33.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
