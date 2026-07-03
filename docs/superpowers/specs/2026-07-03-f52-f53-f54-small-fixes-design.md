# F52 / F53 / F54 — small fixes from the 2026-07 live cycles (design)

Date: 2026-07-03. Backlog: docs/fix-backlog.md (F52, F53, F54 — all born from the
sub-project-5 integration gate and the first two live cycles on the sp5 stack).
Goal: the three defects that bite every daily cycle stop biting the next one.

**Decision provenance:** the approach for each fix was presented as a multiple-choice
question (AskUserQuestion, 2026-07-03); the user was away, so the RECOMMENDED option was
auto-selected in each case, per harness guidance. All three picks match the lean already
written into the committed backlog entries. Override at spec review if any pick is wrong.

---

## F52 — Vintage-scoped document ids (stops cross-day finding-id collisions)

### Problem
`gathering/ingest.py::_doc_id` mints `<host-slug>-<sha256(normalized_url)[:8]>` — no
vintage. `extraction/extractor.py` stamps finding ids `{doc.id}-{n}`. A URL re-gathered
on a later day (daily price page, re-excerpted article) whose content differs reuses the
prior cycle's finding ids; the append-only FindingStore's differing-content collision
check then fails loud in `route_findings` (observed 2026-07-03:
`www-digitimes-com-f88ca4e6-1`, `lambda-ai-845323fc-1`; worked around with a logged
wiki-ingest exclusion). L1's url+hash known-check cannot catch it because gatherer
excerpts vary run-to-run.

### Design (chosen: vintage-scoped docId at the gather seam)
- `_doc_id(normalized_url, as_of)` returns `f"{slug}-{digest}-{as_of}"`
  (e.g. `lambda-ai-845323fc-2026-07-03`). Finding ids inherit it via the existing
  `{doc.id}-{n}` stamp: `lambda-ai-845323fc-2026-07-03-1`.
- `normalize_documents(blobs, *, primary_sources, as_of)` — new **required** keyword.
  Fail loud over a silently un-vintaged id; the two existing test callers
  (tests/test_ingest.py, tests/test_gather_integration.py) update mechanically.
- CLI: `ingest --as-of` becomes **required** (today it defaults to `""` and is read only
  under `--dedup-store`). `_ingest` threads `args.as_of` into `normalize_documents`.
- gather-category SKILL.md: no change expected — it already passes `--as-of` on the
  ingest step (verify in plan; if any invocation omits it, add it).

### Why this seam (and not the extractor)
- One mint point; finding ids inherit for free.
- Recorded fixtures (`fixtures/raw/*`, `fixtures/recorded/*`) carry **pre-built** docIds
  as data, so extract replays and every golden stay byte-identical. Scoping at the
  extractor would re-mint ids on replay and force a suite-wide re-baseline.
- Semantically honest: a re-gathered page with different content IS a new snapshot;
  "document" = (URL, vintage). The URL-stable identity remains recoverable as the
  `slug-digest` prefix, but **no code parses ids apart** (verified: no split/rsplit on
  finding or doc ids anywhere in gpu_agent/).
- Rejected alternative — URL-aware L1 skip: would suppress re-extraction of daily price
  pages, which the daily monitor exists to capture, and needs per-source static/dynamic
  config for no gain.

### Interactions (checked)
- L1 (`filter_seen_documents`, url+hash) is untouched and still skips UNCHANGED content
  cross-day, so vintage scoping never duplicates unchanged findings.
- Wiki: observations are per finding-id; a re-gathered doc's findings now land as new
  same-page observations (correct — they are new-day observations). The 2026-07-03
  ingest-exclusion workaround is no longer needed for future cycles; stored 07-02/07-03
  state is append-only history and is NOT rewritten.
- L2 dedup keys on finding attributes (entity/indicator/…), not ids. Unaffected.
- `normalize_documents` is NOT in the standing frozen core (gate.py, scoring.py,
  schema/*, judgment/briefing.py, judge.py aggregation, pipeline.py, JsonStore). The
  2026-07-01 dedup spec's "byte-unchanged" guard on it was that branch's own additive
  constraint, not a re-freeze.

### Accepted limitation (documented, not fixed here)
Same URL, same asOf, content changed intra-day → ids still collide (fail loud, as
today). Rare; a same-day re-run with identical content remains idempotent by design.

### Tests
- `_doc_id`: deterministic per (url, asOf); same url + different asOf → different ids;
  id format carries the asOf suffix.
- `normalize_documents` threads `as_of` into every minted id.
- CLI: `ingest` without `--as-of` exits 2 (argparse); with it, snapshot filenames carry
  the vintage.
- Existing determinism tests updated to pass `as_of`.

---

## F53 — Cross-cycle indicator + unit consistency for price rows (revives PMI)

### Problem
`price_track.py` matches series on `(indicatorId, publisher, unit)`. The 07-02 cycle
labeled Lambda rental rows `D6` / `USD_per_gpu_hr`; 07-03 labeled the same rows
`gpuSpotPrice` / `USD/GPU-hr`. Both ids are registered, so nothing failed — and PMI got
0 matched series. Two independent drifts, either fatal: the indicator id AND the unit
string. Registry truth: `D6` = GPU **rental** price, unit `USD_per_gpu_hr`;
`gpuSpotPrice` = secondary-market **hardware** price, unit `USD_per_gpu` ("distinct
from D6 (cloud rental)" per its own comparability note).

### Design (chosen: prompt vocabulary + extractor-seam unit check)
Two additive pieces; `gate.py` stays frozen.

1. **Emit-prompt price vocabulary (F55 pattern).** `extraction/prompt.py::build_system`
   gains an optional `price_indicators=None` param: a registry-sourced list of the
   price-side indicator specs (id, label, canonical unit, comparability). When supplied,
   the system prompt appends a block naming the exact vocabulary, e.g.:
   "Price-level rows use EXACTLY one of these indicator ids, with the canonical unit
   string shown: D6 — GPU rental price, unit USD_per_gpu_hr (cloud/rental $/GPU-hr);
   gpuSpotPrice — merchant-GPU hardware spot/resale price, unit USD_per_gpu
   (secondary-market hardware price, distinct from D6)."
   `cli._emit_extract_prompt` sources it from the loaded registry (specs with
   side == "price"), alongside the F55 `valid_targets`. `price_indicators=None` keeps
   the prompt byte-identical (same additive pattern as persona/valid_targets; the
   `SYSTEM` constant is untouched).
2. **Extractor unit check (fail loud → re-dispatch).** In
   `extractor.py::extract_findings`, after `registry.resolve`: a draft whose resolved
   `spec.side == "price"`, with `draft.value is not None` and `spec.unit` set, must have
   `draft.value.unit == spec.unit`; otherwise append violation
   `f"{fid}: price unit '{draft.value.unit}' != registered unit '{spec.unit}' for {draft.indicatorId}"`
   and drop the draft (normal dropped-findings path → coordinator re-dispatches the
   brain with the errors, per doctrine). This catches BOTH failure modes: a rental row
   labeled `gpuSpotPrice` carries `USD/GPU-hr` ≠ `USD_per_gpu` (mislabel caught), and a
   `D6` row with `USD/GPU-hr` ≠ `USD_per_gpu_hr` (unit drift caught).

No recorded fixture carries a price draft (verified), so recorded replays are
untouched. The check is scoped to price-side rows only — extending unit canonicalization
to all measured indicators is a possible future tightening, out of scope here.

Rejected alternative — normalize at price-track level (match on publisher+normalized
unit): hides the mislabel instead of fixing it; stored findings stay inconsistent and
wiki/brief still group by indicatorId.

### Tests
- Unit check: price draft with canonical unit passes; wrong unit string → dropped with
  the named violation; non-price measured drafts with arbitrary units unaffected;
  price draft with value=None unaffected.
- Prompt: `build_system()` byte-identical to `SYSTEM`; with `price_indicators` the block
  lists exactly the registry's price-side ids + canonical units; emit path
  (`extract --emit-prompt`) carries the block (test_prompt_vocab.py style).
- Cross-cycle: two scorecards whose price rows share (D6, lambda.ai, USD_per_gpu_hr) →
  `compute_price_track` matches the series and PMI is non-None (regression for the
  observed 0-matched-series state).

---

## F54 — Seed thesis triggers pass the observable heuristic (data fix + lint)

### Problem
`thesis.py::_trigger_names_observable` (v1 heuristic: registered indicator id substring
OR any digit OR a calendar-cadence word) rejects two committed seed triggers in
`registry/theses.chips.merchant-gpu.json`:
- `supply-constraint-binding`: "CoWoS/HBM lead times normalize to historical norms while
  demand indicators stay positive." (no digit, no cadence word; "lead times" ≠ the id
  `leadTimes`)
- `custom-asic-substitution`: "Hyperscaler capex mix shifts back toward merchant GPUs,
  or a named ASIC program is cancelled/delayed a generation."
A brain echoing them back verbatim is correctly rejected every cycle and must reword —
one avoidable re-dispatch per cycle.

### Design (chosen: reword seeds + seed-lint test)
New trigger texts (semantics preserved, observables named, genuinely more falsifiable):
- `supply-constraint-binding`: "CoWoS/HBM lead times normalize to historical norms for
  2 consecutive quarters while demand indicators stay positive."
- `custom-asic-substitution`: "Hyperscaler capex mix shifts back toward merchant GPUs
  for 2 consecutive quarters, or a named ASIC program is cancelled or delayed by a full
  generation."

New `tests/test_seed_thesis_lint.py`: parametrized over the seed file's theses — every
`falsifiableTrigger` passes `_trigger_names_observable(trigger, registry)`; mechanism /
sensitivity / statement non-empty (mirrors gate rule 3 on the depth fields). Locks all
future seed edits to heuristic-passing form.

**Live book untouched:** `ThesisStore.rebuild` replays `history.jsonl`, whose `seeded`
event embeds the full entries in `record["detail"]` (verified) — the store never
re-reads the registry seed file, so this edit cannot desync the rebuild-verified book at
`store/theses/chips.merchant-gpu/`. The seed file affects only future seedings.

Rejected alternative — grandfather seeds as ungated DATA: doesn't help; the judged
book's depth fields are still gated, so a brain echoing a non-observable seed trigger
still gets rejected every cycle.

---

## Cross-cutting acceptance criteria
1. Full suite green; baseline 804 passed / 3 skipped, strictly additive test count.
2. Frozen-core diff empty: gate.py, scoring.py, schema/*, judgment/briefing.py,
   judgment/judge.py aggregation, pipeline.py, JsonStore.
3. Default prompt paths byte-identical (`extraction.prompt.SYSTEM` and every
   `build_system()` / `build_user_prompt()` no-arg call).
4. Committed fixtures/goldens byte-unchanged (F52's gather-seam placement makes this
   hold; a violation means the seam leaked).
5. Store state (`store/**`) not rewritten — append-only history stands.
6. Next daily cycle expectation (manual verify, not CI): re-gathered URLs mint
   vintage-scoped ids (no FindingStore collision, no ingest exclusions), price rows
   label D6/gpuSpotPrice with canonical units (PMI matches ≥1 series vs prior day once
   two post-fix cycles exist), thesis brain echoing seed triggers passes the gate.

## Build shape
One branch (worktree `.worktrees/f52-f53-f54`), three independent lanes touching
disjoint files — F52 (gathering/ingest.py, cli.py ingest wiring, its tests), F53
(extraction/extractor.py, extraction/prompt.py, cli.py emit wiring, price-track
regression test), F54 (registry seed JSON + new lint test). Sequential tasks per
superpowers:subagent-driven-development; cli.py is the only shared file (two different
functions — F52 `_ingest`/parser, F53 `_emit_extract_prompt`), so F52 and F53 tasks
order sequentially around it. Suite green at every commit; opus final whole-branch
review before merge.
