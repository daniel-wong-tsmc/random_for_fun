# F56 — Validate `--as-of` shape at the seams (+ two cosmetic minors)

Date: 2026-07-12
Branch: `f56-asof-validation`
Backlog item: F56 (defense-in-depth fix wave, three parts)

## Bottom line

F56 is a small defense-in-depth wave with three parts. Investigation found that **two
of the three are already substantially or fully shipped** in prior commits:

- **(a)** `--as-of` shape validation was added to **8 of 10** CLI seams by `db142c3`
  (`fix(F56-core)`, 2026-07-04). Two seams remain unguarded at the argparse layer:
  `corpus` (added later by F62/`eca37c3`) and `eval` (optional `default=""` sentinel,
  deliberately skipped by `db142c3`).
- **(b)** the seed-lint depth-fields comment was already corrected by `0547aea`
  (`fix(F56): correct the depth-fields gate-rule-3 comment`). No code change needed —
  verify only.
- **(c)** `build_system(price_indicators=[])` still renders the malformed `"shown: ."`
  sentence. NOT done.

So the net new work is: close the two remaining `--as-of` seams (a), fix the empty-list
prompt rendering (c), pin all three with tests, and confirm (b) is locked.

## Part (a) — `--as-of` seam inventory and choke-point

### Choke-point

The established choke-point is the argparse-type validator `_as_of(s)` in `gpu_agent/cli.py`
(added by `db142c3`), regex `^\d{4}-\d{2}(-\d{2})?$`, raising
`argparse.ArgumentTypeError(f"--as-of {s!r} must be YYYY-MM or YYYY-MM-DD")`. It names the
flag and the expected shape, and fires at parse time (exit 2) before any work.

We extend this **additively**: no new module, and `gpu_agent/asof.py` (F78's
`AsOfError`/`period_end`/`days_between`) is **not** touched — that keeps the cli.py surface
minimal and avoids colliding with the concurrent F78 stage-6 CLI-wiring lane.

### Full seam inventory (every CLI verb that accepts `--as-of`)

| # | Verb | Required? | Status | Action |
|---|------|-----------|--------|--------|
| 1 | extract | yes | validated (db142c3) | none |
| 2 | ingest | yes | validated | none |
| 3 | wiki-ingest | yes | validated | none |
| 4 | wiki-dedup | yes | validated | none |
| 5 | wiki-lint | yes | validated | none |
| 6 | wiki-lifecycle | yes | validated | none |
| 7 | thesis | yes | validated | none |
| 8 | pipeline | yes | validated | none |
| 9 | **corpus** | yes | **NOT validated at seam** | add `type=_as_of` |
| 10 | **eval** | optional (`default=""`) | **NOT validated** | add `type=_as_of_opt` |

Note: `corpus` is not currently a live path-unsafe-id hole — `corpus.py:125` calls
`period_end(as_of)` and fails loud (exit 1, `AsOfError`) even in coverage-only mode. But
that error says "invalid asOf label", not the flag name, and fires at exit 1 not exit 2.
Adding `type=_as_of` makes rejection uniform with the 8 siblings (exit 2, names `--as-of`)
and stays belt-and-suspenders safe with the downstream check.

### The `eval` seam nuance

`eval`'s `--as-of` is `default=""` and only consulted for `record-grade` (report
provenance, `build_report(..., as_of=...)`) — it does **not** mint a path/id, and the
handler already fails loud when it is empty for `record-grade` (`cli.py:651`). Its empty
default is a legitimate "not supplied" sentinel for the other eval actions
(emit-brain/verdict/rebaseline).

We add a small sibling validator `_as_of_opt(s)` that **permits `""`** (returns it
unchanged, so argparse applying `type` to the string default does not blow up the whole
subcommand) but **rejects any malformed non-empty value** with the same flag-naming
message. This delivers the acceptance's "reject bad shapes at every seam" for eval
(a fat-fingered `2026/07/03` is rejected) without breaking the sentinel.

## Part (b) — seed-lint comment (already done)

`0547aea` already corrected the comment in both `gpu_agent/thesis.py:385-389`
(`_gate_depth_fields` docstring) and `tests/test_seed_thesis_lint.py:33-36`. Both now
state that rule 3 checks mechanism/falsifiableTrigger/sensitivity non-empty + observable
trigger, and explicitly note that rule 3 does **not** check `statement`
(statement is rule 4's job). The existing `test_seed_depth_fields_non_empty` pins the
seed-data checks. Action: verify, no code change.

## Part (c) — `build_system(price_indicators=[])` empty-list rendering

`gpu_agent/extraction/prompt.py:71` uses `if price_indicators is not None:`, so an empty
list falls into the block and renders `"...shown: " + "; ".join([]) + "."` → the malformed
`"...shown: ."`. Fix: change the guard to `if price_indicators:` (truthy). Effects:
- `None` (default): no block — **unchanged**.
- `[]`: no block — **fixes the malformed sentence** (was unreachable; registry always has
  price indicators today, so default emitted prompts stay byte-identical).
- non-empty list: block rendered — **unchanged, byte-identical**.

The frozen brain-prompt default (`SYSTEM = build_system()`) is byte-identical either way,
so `tests/test_evals_baseline_pin.py` must stay green.

## Testing

- (a) corpus: subprocess CLI test — `corpus --as-of 2026/07/03` → exit 2, stderr names
  `--as-of`; good shapes (`2026-07`, `2026-07-03`) accepted.
- (a) eval: subprocess CLI test — `eval record-grade --as-of 2026/07/03 ...` → exit 2,
  stderr names `--as-of`; and `eval emit-brain` with no `--as-of` still parses (empty
  sentinel preserved).
- (a) parametrized rejection of the acceptance bad-shape set (`2026/07/03`, `20260703`,
  `2026-7-3`, ``, `2026-07-3`) at the seam(s).
- (b) confirm `test_seed_depth_fields_non_empty` present + green (existing).
- (c) `build_system(price_indicators=[]) == SYSTEM` (byte-identical, no `"shown: ."`);
  keep the existing None + non-empty pins.
- Full suite green (baseline 1200 passed / 5 skipped).

## Recorded design forks (AFK-precedent — user to confirm at merge review)

1. **eval seam validated via optional `_as_of_opt`** (permit `""` sentinel, reject
   malformed non-empty) rather than left untouched. Rationale: acceptance says "every
   seam"; the sentinel and the record-grade empty-check are both preserved.
   *Alternative rejected:* leave eval as `db142c3` did — but that leaves a documented
   seam unguarded against a fat-fingered non-empty value.
2. **`--prev-as-of` (wiki-lint) left unvalidated at argparse.** It is a diff-window
   lookup label, not an id-minting `--as-of`; it flows through the shared date logic that
   fails loud downstream. Out of F56's `--as-of` scope.
3. **Part (c) scoped to `price_indicators` only.** The sibling empty-list cases
   (`valid_targets=[]`, `scoring_indicators=[]`) have the same latent shape but are out of
   F56's stated scope and equally unreachable; not touched to keep the byte-identical
   prompt surface minimal. Flagged for a possible future tidy.
4. **`corpus` gets an argparse `type=_as_of`** (exit 2, names flag) layered over the
   existing downstream `period_end` guard (exit 1). Uniformity with the 8 sibling seams.

## Constraints honored

- Frozen core untouched (gate/scoring/schema/briefing/pipeline/sufficiency/JsonStore, store/).
- Default emitted brain prompts byte-identical; baseline-pin stays green.
- cli.py surface kept minimal (two `type=` additions + one tiny `_as_of_opt` helper) —
  merge AFTER F78 stage 6, rebase first.
