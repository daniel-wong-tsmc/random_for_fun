# Contract v1.3 migration — 2026-07-04

The second sanctioned frozen-core migration (charter Part 33; user-approved 2026-07-04 in
the F63 design — `docs/superpowers/specs/2026-07-04-f63-corroboration-doctrine-design.md`).
It amends exactly ONE rule; everything else in the frozen set is byte-identical to v1.2.

## Rule change

- **F2e** — a finding whose evidence is entirely `secondary` cannot carry `confidence=high`
  **unless its evidence spans ≥ N distinct publishers** (N=3, `registry/corroboration.json`;
  publisher identity = F31's `publisher_key`, so syndication at one domain counts once).
  Error text now names the shortfall: `(K distinct publishers < N)`.

## Deliberately unchanged

- **F3** (dimension-level cap: `dimensionStatus.confidenceCap="medium"` + note
  `"secondary-only evidence"` when a dimension's citations carry no primary) — dimension
  confidence DISPLAY stays conservative; corroboration unlocks finding confidence and
  movement, not the cap badge.
- All other v1.2 rules, the schema (`schemaVersion` stays 1.2 — no schema field changed),
  scoring, briefing, judge aggregation, pipeline, JsonStore.

## Companion doctrine (same branch, not frozen-core)

- Thesis anti-whipsaw rule 6: corroborated (≥N publishers) secondary-only reversals apply.
- Evidence-sufficiency gate (`gpu_agent/sufficiency.py`): rating/binding-constraint changes
  vs MEMORY require primary evidence or ≥N distinct publishers; reject → re-dispatch.
- Charter Part 37 amendment: the staged-trust "next increment" has landed.
