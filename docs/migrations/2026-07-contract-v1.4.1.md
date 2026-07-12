# Contract v1.4.1 migration — 2026-07-12

The fourth sanctioned frozen-core migration (charter Part 33) — a **micro-migration** that closes
the one hole v1.4's F72 half left open. User-approved 2026-07-12 (interactive AskUserQuestion,
orchestrator session — NOT AFK): fix now as its own small Part-33 migration with a read-only
shadow-check, rather than bundling into F79. Design of record:
`docs/superpowers/specs/2026-07-12-f72-sufficiency-collapsed-publishers-design.md`; built via
`docs/superpowers/plans/2026-07-12-f72-sufficiency-collapse.md`. **Only the user merges** (never
AFK); final review mandatory. Everything else in the frozen set is byte-identical to v1.4.

## The hole this closes

v1.4 (F72) made publisher distinctness syndication-aware and routed **gate F2e**, **thesis rule 6**,
and **wiki page promotion/corroboration** through the shared `collapsed_publisher_set` helper — but
`gpu_agent/sufficiency.py::_sufficient` still counted **raw `publisher_key` netlocs** (flagged as an
explicit follow-up at the v1.4 merge). The result: one press release republished on 3 domains
**passed** the evidence-sufficiency gate's distinct-publisher bar while F2e would have collapsed it to
one publisher. Same doctrine, one gate left open.

## Rule change (the ONLY frozen-core edit in this lane)

- **Evidence-sufficiency gate** (`sufficiency.py::_sufficient`) — the distinct-publisher count is now
  computed over the **same collapsed publisher identities the F2e gate uses**. The counting line
  `{publisher_key(e) for e in evs}` becomes `collapsed_publisher_set(evs)` (the shared helper in
  `gpu_agent/publisher.py`; **zero duplicated collapse logic**). So a wire story syndicated across
  known syndicator domains, or reprinted byte-for-byte across different netlocs, now counts as **one**
  publisher for sufficiency too — a rating/binding-constraint change backed only by that syndicated
  set no longer clears `minDistinctPublishers: 3` (`registry/corroboration.json`). The error text is
  unchanged in shape: `(K distinct publishers < N)`.

Only the counting seam moves. Primary-evidence-passes-outright, the unresolvable-id handling, the
F71 anchor-forced-move exemption, thresholds, and every emitted prompt are untouched.

## Deliberately unchanged

- No emitted-prompt change (F6 pin `tests/test_evals_baseline_pin.py` stays green). No schema change
  (`schemaVersion` stays 1.2). No `store/` edit. No threshold, anchor-semantics, or prompt change.
- The three sibling corroboration surfaces already routed through `collapsed_publisher_set` in v1.4
  and were re-verified here, not rebuilt: gate F2e (`gate.py`), thesis rule 6 (`thesis.py`), wiki
  promotion/corroboration (`wiki/lifecycle.py`).
- Scoring, briefing, judge aggregation, pipeline, JsonStore — byte-identical to v1.4.

## Shadow-check (READ-ONLY — no store file edited, no scorecard re-issued)

Recomputed the sufficiency distinct-publisher counts over **all committed store data** under both the
old (raw `publisher_key`) and new (`collapsed_publisher_set`) counting, to see whether any past
verdict would have flipped. Because collapsed counting can only **merge** identities (collapsed count
≤ raw count, always), a verdict can flip only pass→fail, and only where a cited finding-set's raw
count met the bar N but its collapsed count fell below N with no primary evidence. So the check
enumerates every dimension citation set in every committed scorecard and looks for that exact shape —
no reconstruction of the memory-bundle chaining is needed for a decisive answer.

Coverage: 21 committed scorecards (`store/chips.merchant-gpu/`), 93 dimension citation sets, 267
findings resolved — **0 unresolved cited findingIds** (full reconstruction; nothing approximated).

Result: **no past sufficiency verdict flips.**

- Dimension citation sets where raw ≥ 3 but collapsed < 3 with no primary (the only flip shape): **0**.
- Actual rating changes across consecutive committed scorecards: **30**; of those, changes that would
  flip pass→fail under collapsed counting: **0**.
- Sets where any collapse happened at all (collapsed < raw): **1** — `2026-07-v3.json`, `momentum`,
  which drops from 4 to 3 distinct publishers but still clears the bar (3 ≥ 3), so its verdict is
  unchanged.

Interpretation: the tightening is real (one set does collapse) but no committed cycle relied on
syndicated distinctness to clear the sufficiency bar, so re-running history under v1.4.1 would have
produced the same verdicts. The change is forward-looking protection, not a retroactive correction.
