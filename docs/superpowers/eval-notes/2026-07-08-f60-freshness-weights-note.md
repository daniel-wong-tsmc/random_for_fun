# F60 data half — freshness weights verification note (2026-07-08)

**Lane:** `fix/freshness-weights` (S1). **Plan:** `docs/superpowers/plans/2026-07-08-f60-freshness-weights.md`.
**Approach:** Option A (reweight existing leading set), user-approved 2026-07-08.

## The change

`registry/indicators.json`, weight-only:

| indicator | dimension / side | old → new |
|---|---|---|
| `rpoBacklog` | momentum / demand | 0.10 → **0.14** |
| `vendorRevenueGuidance` | momentum / demand | 0.12 → **0.16** |

Rationale for the targets: lift the two forward/leading DEMAND indicators to ≈ ½·`apiArr`
(0.20, the largest coincident demand weight) so forward signal counts materially without a single
quarter's backlog/guidance dominating realized momentum. Values are tunable — the acceptance signal
is DMI movement, not the specific numbers.

## Why this stayed in the data half (F6 pin green)

The emitted brain prompts serialize `{id, label, side, unit}` per indicator (`gpu_agent/evals/emit.py:26-38`,
`gpu_agent/cli.py:286-294`) — **`weight` is not emitted**. So a weight-only change produces no prompt-byte
change and `tests/test_evals_baseline_pin.py` stays green (verified). `scoring.py` is untouched: the
exclusion rule (`scoring.py:14`) and contribution formula (`:22-23`) are frozen; their side-semantics
ship only as the future **v1.5** migration.

## Measured effect

Canonical two-finding recompute through the real (frozen) `dmi_smi_contribution`, reading the registry
default (no override): DMI **0.22 → 0.30** (`test_reweighted_leading_demand_moves_dmi_via_registry_default`).
Confirmed effective in live scoring: `fixtures/asg.chips.merchant-gpu.json` overrides only `{D2,D6,S9,S10}`,
so `rpoBacklog`/`vendorRevenueGuidance` fall back to the registry default and the reweight is not inert.
F62's 45-day corpus keeps a captured 10-Q/earnings leading finding in-window, so these now contribute
across daily cycles rather than only in the quarter they land.

## One consequence handled — history preserved

The reweight pushed the live recompute in the v1.2 replay-fidelity test (`test_replay_v12.py`)
0.5067 → 0.6000, diverging from the immutable 2026-06 historical scorecard (`store/…/2026-06-v12.json`),
because that test recomputed with live registry defaults for the fallback indicators. **The stored
scorecard was NOT edited.** Instead the test was frozen to `_WEIGHTS_AS_OF_2026_06` — the exact weight
vector in force at replay generation — verified to reproduce dmi 0.506667 / smi -0.073333 / sdgi 0.58.
This decouples the historical-fidelity check from all future registry evolution.

## Deferred — MUST NOT LOSE (wave-plan §6)

1. **`scoring.py` side-semantics half → future v1.5 migration.** F60's checkbox stays **unchecked**.
2. **SMI-leading residual.** The backlog's `smiContribution: 0.0` is a SUPPLY gap: there is no leading
   *supply* indicator, so a demand reweight cannot move it. Needs an Option-C news-sourced leading
   supply indicator or the v1.5 scoring half.

## Suite

Baseline on lane base (`49f4880`): 1150 passed / 5 skipped. After the change: **1152 passed / 5 skipped**
(+2 guard tests; the replay test reconciled, not counted new). F6 pin green throughout.
