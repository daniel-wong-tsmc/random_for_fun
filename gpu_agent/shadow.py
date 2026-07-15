"""F79 Stage 6 — v2 shadow recording (spec "Shadow mode").

Each live cycle computes the v2 indices ALONGSIDE v1 and records them as string keys
in the scorecard's free-form provenance dict (additive — NOT a schema change): v2.dmi,
v2.smi, v2.sdgi, v2.alertRaw. ONLY v1 renders until the G4 cutover — the render
tripwire in tests/test_shadow_wiring.py pins that report.py/reader.py never read these.

Invoked by the append-only `gpu-agent v2-shadow` verb as a WITHIN-CYCLE, pre-commit
step (the run-cycle skill hook lands in the final pre-G4 stage): the stamped file is
what the cycle commits, so committed store history is never rewritten.

The v2 history is recomputed on every call (monthly vintage walk, exactly the backtest
convention: prior months at month-end, the CURRENT month at the cycle's exact as-of
day so a mid-month cycle never sees later-in-month publications) — pure projection,
no stored state, replayable; an empty/absent series store is a byte-identical no-op.
"""
from __future__ import annotations

import pathlib
from typing import Optional

from gpu_agent.backtest import _month_end, _month_range
from gpu_agent.change import raw_alert_v2
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.scoring import score_v2
from gpu_agent.series_registry import SeriesRegistry
from gpu_agent.series_store import latest_by_period

SERIES_REGISTRY_PATH = "registry/series-indicators.json"
SERIES_ROOT = "store/series"
WALK_START = "2023-01"     # the backfill epoch — the backtest's walk start


def _store_has_points(registry: SeriesRegistry, series_root, as_of: str) -> bool:
    root = pathlib.Path(series_root)
    if not root.is_dir():
        return False
    return any(latest_by_period(root, spec.id, as_of=as_of)
               for spec in registry.specs.values())


def compute_v2_shadow(as_of: str, *, series_registry_path=SERIES_REGISTRY_PATH,
                      series_root=SERIES_ROOT) -> dict[str, str]:
    """The v2 shadow keys for a cycle at `as_of` (YYYY-MM or YYYY-MM-DD), or {} when
    the series store has nothing visible at that vintage (no-op guard: replayed and
    pre-backfill cycles stay byte-identical)."""
    registry = SeriesRegistry.load(series_registry_path)
    final_as_of = as_of if len(as_of) == 10 else _month_end(as_of)
    if not _store_has_points(registry, series_root, final_as_of):
        return {}
    month = as_of[:7]
    dmi_s: list[float] = []
    sdgi_s: list[float] = []
    for m in _month_range(WALK_START, month):
        month_as_of = final_as_of if m == month else _month_end(m)
        dmi, smi = score_v2(registry, series_root, as_of=month_as_of)
        dmi_s.append(dmi)
        sdgi_s.append(dmi - smi)
    color, _triggers = raw_alert_v2(sdgi_s, dmi_s)
    dmi, sdgi = dmi_s[-1], sdgi_s[-1]
    return {"v2.dmi": f"{dmi:.6f}", "v2.smi": f"{dmi - sdgi:.6f}",
            "v2.sdgi": f"{sdgi:.6f}", "v2.alertRaw": color}


def stamp_scorecard(path, *, series_registry_path=SERIES_REGISTRY_PATH,
                    series_root=SERIES_ROOT) -> bool:
    """Merge the v2 shadow keys into a stored scorecard's provenance, in place
    (within-cycle, pre-commit). Touches ONLY v2.* keys; idempotent; returns False and
    leaves the file untouched when the series store yields nothing."""
    p = pathlib.Path(path)
    sc = Scorecard.model_validate_json(p.read_text(encoding="utf-8"))
    keys = compute_v2_shadow(sc.asOf, series_registry_path=series_registry_path,
                             series_root=series_root)
    if not keys:
        return False
    if all(sc.provenance.get(k) == v for k, v in keys.items()):
        return True   # idempotent re-stamp: identical bytes, no rewrite
    sc.provenance.update(keys)
    p.write_text(sc.model_dump_json(indent=2), encoding="utf-8")
    return True
