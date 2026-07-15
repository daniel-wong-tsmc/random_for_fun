"""F79 Task 3.1 — THE v1.x replay-fidelity pin, landed BEFORE any v2 path ships.

Every stored v1.x scorecard that is a canonical output of the current v1 contract must
keep reproducing its stored DMI/SMI/SDGI through gpu_agent.scoring.dmi_smi_contribution,
byte-for-value. If this file goes red after touching scoring.py, the v2.0 migration has
disturbed the frozen v1 path — that is a merge-blocker, never a test to adjust.

Weight-vector provenance (empirically verified against every stored scorecard,
2026-07-13, all exact):
- The five pre-contract-v1.2 ORIGINALS (2026-06-v2..v6) are irreproducible under the
  current v1 code BY DESIGN: contract v1.2's per-(entity, indicator) fix (F7 entity
  shadowing) changed the math, which is why the v1.2 migration minted replay scorecards
  (v7..v12). The originals are pinned STRUCTURALLY here (replayOf links + verbatim
  findings); their numeric fidelity lives in their replays.
- W_PRE_F60 reproduces: 2026-06-v1, the v1.2 replays (2026-06-v7..v12), the dailies
  (2026-07-02/03/05/06), and 2026-07-v1..v4 (F60 reweighted rpoBacklog 0.10->0.14 and
  vendorRevenueGuidance 0.12->0.16 in early July, AFTER those runs).
- W_CURRENT (assignment overrides over today's registry defaults) reproduces
  2026-07-v5 and 2026-07-v6 (post-F60 live cycles).
Scorecards that postdate this pin are covered by CURRENT via test_all_pinned_files_known
failing loudly on any new store file, forcing a deliberate mapping decision.
"""
from __future__ import annotations
import pathlib
import pytest
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.registry.indicators import IndicatorRegistry

STORE = pathlib.Path("store/chips.merchant-gpu")
CATEGORY = "chips.merchant-gpu"

# Assignment overrides (asg.chips.merchant-gpu@1.0/1.1 — identical weights dict).
_ASG = {"D2": 0.10, "D6": 0.12, "S9": 0.04, "S10": 0.08}
# Registry defaults in force before F60's 2026-07 reweighting, frozen forever here.
W_PRE_F60 = dict(_ASG, **{
    "market-share-pct": 0.10, "grossMargin": 0.10, "leadTimes": 0.08,
    "rpoBacklog": 0.10, "vendorRevenueGuidance": 0.12,
    "apiArr": 0.20, "releaseCadence": 0.10,
})
W_CURRENT = _ASG  # overrides on top of the live registry defaults

# file -> weight vector that reproduces it (empirical matrix, 2026-07-13).
PINNED = {
    "2026-06-v1.json": W_PRE_F60,
    "2026-06-v7.json": W_PRE_F60,
    "2026-06-v8.json": W_PRE_F60,
    "2026-06-v9.json": W_PRE_F60,
    "2026-06-v10.json": W_PRE_F60,
    "2026-06-v11.json": W_PRE_F60,
    "2026-06-v12.json": W_PRE_F60,
    "2026-07-02-v1.json": W_PRE_F60,
    "2026-07-03-v1.json": W_PRE_F60,
    "2026-07-05-v1.json": W_PRE_F60,
    "2026-07-06-v1.json": W_PRE_F60,
    "2026-07-v1.json": W_PRE_F60,
    "2026-07-v2.json": W_PRE_F60,
    "2026-07-v3.json": W_PRE_F60,
    "2026-07-v4.json": W_PRE_F60,
    "2026-07-v5.json": W_CURRENT,
    "2026-07-v6.json": W_CURRENT,
    "2026-07-v7.json": W_CURRENT,   # 2026-07-14 daily cycle (merged from main); post-F60 -> CURRENT
    "2026-07-v8.json": W_CURRENT,   # 2026-07-15 daily cycle (merged from main); post-F60 -> CURRENT
}
# Pre-v1.2 originals: superseded by replays, pinned structurally (original -> replay).
SUPERSEDED = {
    "2026-06-v2.json": "2026-06-v8.json",
    "2026-06-v3.json": "2026-06-v9.json",
    "2026-06-v4.json": "2026-06-v10.json",
    "2026-06-v5.json": "2026-06-v11.json",
    "2026-06-v6.json": "2026-06-v12.json",
}


def _load(name: str) -> Scorecard:
    return Scorecard.model_validate_json((STORE / name).read_text("utf-8"))


@pytest.fixture(scope="module")
def registry():
    return IndicatorRegistry.load("registry/indicators.json")


@pytest.mark.parametrize("name", sorted(PINNED))
def test_v1_scorecard_replays_exactly(name, registry):
    sc = _load(name)
    dmi, smi = dmi_smi_contribution(sc.findings, registry, CATEGORY, PINNED[name])
    assert sc.demandSupply.dmiContribution == pytest.approx(dmi), name
    assert sc.demandSupply.smiContribution == pytest.approx(smi), name
    if sc.demandSupply.sdgi is not None:
        assert sc.demandSupply.sdgi == pytest.approx(dmi - smi), name


@pytest.mark.parametrize("original,replay", sorted(SUPERSEDED.items()))
def test_superseded_original_is_pinned_by_its_replay(original, replay):
    o, r = _load(original), _load(replay)
    assert r.provenance.get("replayOf") == original.removesuffix(".json")
    assert r.provenance.get("migration") == "contract-v1.2"
    # historical judgment is immutable: the replay re-ran MATH, not the gate
    assert [f.id for f in r.findings] == [f.id for f in o.findings], original


def test_all_pinned_files_known():
    """Fail loudly when a NEW scorecard lands: it must be added to PINNED deliberately
    (post-F60 runs belong to W_CURRENT) so replay fidelity never silently lapses."""
    import re
    on_disk = {p.name for p in STORE.glob("*.json")
               if re.match(r"^\d{4}-\d{2}(-\d{2})?-v\d+\.json$", p.name)}
    assert on_disk == set(PINNED) | set(SUPERSEDED), (
        "store/chips.merchant-gpu changed: new/renamed scorecards must be added to the "
        f"replay pin. delta: {sorted(on_disk ^ (set(PINNED) | set(SUPERSEDED)))}")
