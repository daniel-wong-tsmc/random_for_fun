# Contract v1.4 migration — 2026-07-06

The third sanctioned frozen-core migration (charter Part 33). One coupled Part-33 change
bundling **two** frozen-core gate-semantics fixes — **F72** (syndication-resistant publisher
distinctness) and **F71** (anchor-bound vs evidence-sufficiency precedence) — with **F75**'s
companion doctrine (whole-run bypass removal + trust-footer disclosure) riding the same branch.
User-approved 2026-07-06: all six §7 decisions signed off in the design spec
`docs/superpowers/specs/2026-07-06-contract-v1.4-migration-design.md` (D1/D3/D5 + Q1–Q6), built
via `docs/superpowers/plans/2026-07-06-p3-contract-v1.4-plan.md`. **Only the user merges** (never
AFK). Everything else in the frozen set is byte-identical to v1.3.

## Rule changes (one line each, by F-id)

- **F2e / F72** — publisher distinctness is computed over **collapsed** publisher identities, not
  raw netlocs. Gate F2e's set (`{publisher_key(e) for e in f.evidence}`) becomes
  `collapsed_publisher_set(...)`, which (a) maps any netloc in `registry/syndicators.json` to a
  shared **originating-publisher** identity and (b) collapses byte-identical wire reprints across
  different netlocs to one identity (L1 exact-hash over each citation's excerpt). One wire story on
  three syndicator domains → **1** distinct publisher, so `minDistinctPublishers: 3` can no longer
  be satisfied by syndication. Error text keeps the v1.3 shape: `(K distinct publishers < N)`.
- **F71** — an **anchor-FORCED** rating move (the Part 7 bias guardrail makes the prior rating
  illegal, so `gate.py` bounds it) is **exempt from the evidence-sufficiency gate**: it is
  code-computed measured evidence, not a judgment re-rate. The exempted rating is stamped
  **`anchor-bounded on thin evidence`** on the existing `dimensionStatus` note (no schema field).
  A genuine qualitative re-rate on the same thin evidence is **still blocked** (over-loosening
  guard). The uncaught anchor-conflict traceback path gets a clean `anchor:` handler.

## The silent hole F72 closes (biggest behavioral delta)

Unlike v1.3 (which *loosened* F2e with a corroboration exception), v1.4's F72 half **tightens** the
same gate against a silent bypass. The only prior defense against cross-domain wire syndication was
an **un-gated extraction-prompt sentence** ("distinct outlets, not syndication of one story") — the
exact "nothing un-gated reaches a number" anti-pattern the doctrine forbids. v1.4 moves that defense
into deterministic code (registry + near-dup). This is the mirror image of F71: F71 is *honest* thin
evidence failing loudly; F72 is *disguised* thin evidence (one story, three netlocs) that today
passes **unremarked** — no bypass record, nothing for review to catch. All three `publisher_key`
consumers inherit the collapse via the shared `collapsed_publisher_set` (verified, not assumed):
gate F2e, thesis rule 6 (`_publisher_domains`), and wiki promotion (`corroboration`). Closing the
hole also gives F69's open note a home: the gatherer records the **originating publisher** as
structured `RawDocument` metadata (`originatingPublisher`), not free text in `content`.

## schemaVersion decision

**`schemaVersion` stays `1.2` — no schema field is added or changed** (§3, D3).
- F72's originating-publisher datum lives on **`RawDocument` gather-blob metadata** (the
  gatherer-contract surface), **not** on the `Finding` model.
- F71's `anchor-bounded on thin evidence` stamp rides the **existing** `dimensionStatus.note`
  surface (the same one that already carries `"secondary-only evidence"`), not a new field.

## Deliberately unchanged (what a reader might assume moved but didn't)

- **Scoring math** — DMI/SMI/anchors/divergence are byte-identical. F71/F72 are gate/corroboration
  semantics; no scoring indicator, weight, or side-rule changes. `fixtures/golden/*`
  (anchors/findings/ratings/scorecard/status.json) is **regenerated NOT AT ALL** — there is no
  math delta to re-pin (contrast v1.2, which regenerated goldens with a hand computation).
- **The F63 corroboration exception itself** (all-secondary can be `high` at ≥N publishers) — v1.4
  changes only *how publishers are counted*, not the exception's existence.
- **`minDistinctPublishers: 3`** — the threshold is unchanged; only the denominator becomes
  syndication-resistant.
- **The Finding schema, judge aggregation, pipeline math, JsonStore** — byte-identical to v1.3.
- **F3 dimension-level confidence-cap badge** — unchanged; the F71 stamp is additive to its note.
- **The extraction prompt** — unchanged (§7 Q5), so `tests/test_evals_baseline_pin.py` stays green;
  no emitted prompt bytes moved, no run-eval needed.

## Shadow-run (gate behavior, NO store writes) + honesty section

`scripts/shadow_run_v14.py` recomputes, over every stored finding and dimension rating in
`store/chips.merchant-gpu/*.json`, the distinct-publisher count **old** (raw netloc) vs **new**
(collapsed), and the F71 anchor-forced-move pattern across consecutive stored versions. It writes
nothing (Part 33: originals immutable).

**F72 flip table (bar N=3):**

| scope | scanned | count changed by collapse | verdict flips (relied on the hole) |
|---|---|---|---|
| stored findings | 545 | 0 | 0 |
| stored dimension ratings | 81 | 1 | **0** |

The single collapse-affected count:

| scorecard | dimension | raw → collapsed | crossed the ≥3 bar? |
|---|---|---|---|
| 2026-07-v3 | momentum | 4 → 3 | **no** (stays ≥3) |

**Honesty verdict: NOTHING currently stored relied on the F72 syndication hole.** No stored
high-confidence finding, thesis reversal, or wiki promotion flips pass→fail under v1.4. The one
place the collapse bites — 2026-07-v3's `momentum` dimension — had four cited netlocs
(`blogs.nvidia.com`, `digitimes.com`, `finance.yahoo.com`, `stocktitan.net`); the two syndicators
collapse to one `wire:syndicated` identity, taking the count from 4 to **3**, which still meets the
≥3 corroboration bar. Its verdict is unchanged. This confirms the campaign's Phase-3 assessment:
F72 was a **proven structural risk, not yet a witnessed silent failure** — the shadow-run confirms
it is still structural (not yet witnessed) as of this migration.

**F71 shadow:** the anchor-forced + under-sourced pattern (prior rating illegal under the current
anchor, new rating legal, citations under-sourced) appears twice in stored data — `2026-06-v3`
`moat` Very strong→Weak at anchor −0.25 and its v1.2 replay `2026-06-v9` (the same underlying
cycle). Honesty caveat: these are 2026-06 cycles; the F63 evidence-sufficiency gate that *turns*
such a move into a deadlock did not exist until contract v1.3 (2026-07), so none actually
deadlocked at the time. The **one recorded live firing** (2026-07 v3 monthly, `moat` Weak→Mixed at
+0.50) lives in the cycle-log gate record at git `99ca522`, not reconstructable from the immutable
scorecard series alone (the shipped v3 `moat` is the post-resolution `Mixed`, capped medium). Under
v1.4 that firing resolves via the exemption (stamped, no bypass) instead of a whole-run
`--no-sufficiency`.

## Replay decision — none (follow v1.3), retro-note instead

**No replay / no re-gating of stored scorecards.** A gate-rule change with no scoring-math delta has
nothing to replay, and charter Part 33 keeps originals immutable. Because the shadow-run shows **no**
stored scorecard relied on the F72 hole, there is nothing to retro-disclose for F72. For the one
recorded F71 sufficiency bypass (2026-07-v3), the disclosure surface is render-time, not the store:
the next monthly brief's trust footer carries the F75 waiver line when its cycle-log gate record
names the bypass (see Companion doctrine). This document is the durable render surface recording
that hindsight now (§6). Originals stay byte-unchanged.

## Companion doctrine (same branch, not frozen-core)

- **F75 — whole-run `--no-sufficiency` removed** from live paths (judge + pipeline; §7 Q3). The gate
  always runs; F71's exemption covers its one sanctioned use, and any residual re-dispatches rather
  than skipping wholesale — no whole-run bypass survives before the supervised-unattended pilot.
- **Trust-footer waiver disclosure** — `brief.gate_waivers_from_cycle_log` + `render_market_caveat`:
  any gate the run's cycle log records as bypassed/waived (`gates.*`) surfaces one exec-plain waiver
  line above the appendix divider; the `report` CLI's `--cycle-log` sources it. A bypassed cycle can
  no longer present a clean footer. A clean cycle renders today's footer byte-for-byte.
- **`sufficiency.py` added to the frozen-core Standing Constraints** list (`docs/roadmap.md`; §7 D1)
  — its exemption logic is gate semantics as directly as `gate.py`.
- **2026-07-v3 retro note** — disclosed here (render-time surface, per §6) rather than by mutating
  the immutable store; the next monthly brief surfaces it via the F75 waiver mechanism from its
  cycle-log gate record.
- **Charter reconciliation** — Part 33 now registers migration #3; Part 37's corroboration doctrine
  is updated so "syndication of one story counts once" is code-true (v1.4), and its deferred clause
  is reconciled in the same edit (normalized/shingle near-dup similarity is what remains deferred —
  §7 Q6; registry + exact-hash landed). F63 left Part 37 self-contradictory for weeks; this does not
  repeat that.

## Deferred to a bounded follow-up (recorded)

- **Normalized/shingle near-dup similarity** (§7 Q6): v1.4 ships registry + **exact-hash** near-dup
  collapse. Wire reprints with different site wrappers that are *not* byte-identical and *not* on a
  known syndicator netloc still count as distinct until a normalized-similarity pass lands — a
  bounded follow-up if a future shadow-run shows unknown-syndicator reprints slipping through.
