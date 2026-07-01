# Provisional lifecycle engine — promotion + pruning + quarantine (sub-project 4-4c) — design

- **Date:** 2026-07-01
- **Status:** Draft for review (the lifecycle half of sub-project 4-4's discovery lane)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md);
  charter **Part 18** (room to explore — provisional threads, confidence-capped, quarantined from canonical,
  promoted on persist+corroborate; pruning is the reverse), **Part 10** (the signal test — persistent + corroborated
  + material + mechanistic), **Part 16** (promotion pipeline generalized to entities/metrics/themes), **Part 20**
  (replayable), **Part 29** (nothing silent), **Part 33** (additive-only).
- **Depends on:** 4-1 (`WikiStore`/`WikiPage` with `status: provisional|registered`, `update_header`,
  `observations`, `state_history`, `index`), 4-4a (`route_findings` auto-creates *provisional* entity pages),
  4-4b (`lint()` → the `stale` signal + materiality substrate), 4-4d (L2 dedup so a new-cycle observation means a
  genuinely NEW/UPDATE fact). **Feeds:** 4-5 (the brief renders `registered` as coverage, `provisional` as
  "not yet in coverage / confidence-capped", and can call the quarantine filter) and the future discovery half.

---

## 0. What 4-4c is — the scope split, and the locked decisions

Sub-project **4-4** ("daily gather + relevance/lint + brain ingest + discovery engine") decomposes into
4-4a (ingest writer, done) → 4-4b (relevance/lint, done) → 4-4d (input firehose, done) → **4-4c (this spec)**.
4-4c is the **discovery lane**, but the discovery lane splits into two cleanly separable halves:

- **The lifecycle engine (THIS spec — 4-4c):** a **pure-code** engine that manages the lifecycle of the
  *provisional* pages that already exist — **promotion** (provisional → registered on persist+corroborate),
  **pruning** (non-destructive fade of stale provisionals), and **quarantine** (keep provisional/off-registry
  material out of the canonical projection). Deterministic, pytest-tested, like 4-4b/4-4d.
- **The brain-driven discovery step (DEFERRED to a later sub-project):** a new `--emit-prompt` seam + the
  `explore` budget where the brain *opens* provisional theme / off-registry-entity threads from 4-4d's candidate
  stream, plus bounded rabbit-holing. This is the *creation* of new provisional topics; it is **out of scope here.**

**Rationale for the split (locked):** the lifecycle engine can be built and tested entirely over provisional pages
that already exist (4-4a auto-creates provisional entity pages; 4-4d's UPDATEs keep them moving), with no new brain
seam — matching the low-risk pure-code rhythm of 4-4b/4-4d. The brain discovery step is a larger, separate design.

**Locked decisions (from this session's brainstorm — don't relitigate):**
- **(a) Scope = the pure-code lifecycle engine only** (promotion + pruning + quarantine). Brain discovery + the
  `explore` budget are a later sub-project.
- **(b) Promotion test = persist + corroborate, read from persisted state:** **PERSIST** = the page has
  observations across **≥ `min_persist_cycles` distinct `asOf` cycles** (default 2); **CORROBORATE** = the page's
  findings cite **≥ `min_sources` distinct evidence sources** (default 2). Both must hold. (Chosen over
  "material across N cycles" because the per-cycle `lint` event carries `pageId=None` — the material-per-cycle list
  is *not* persisted, so a material-history signal would require recomputing `lint` per historical cycle; and
  post-4-4d, an observation in a new cycle already implies a genuinely NEW/UPDATE material fact. Chosen over
  "≥2 primary-tier" because novel/off-registry topics surface first in *secondary* sources, so a primary-only bar
  would make genuine discoveries nearly un-promotable.)
- **(c) Propose, don't auto-register:** the engine emits a promotion-candidate report by default and flips
  `status=registered` **only** behind an explicit `--apply` flag — the charter's "proposed → reviewed → promoted"
  review gate (Part 18/16). Nothing is silently promoted.
- **(d) Non-destructive pruning:** a stale provisional is flagged a prune candidate in the report; `--apply` floors
  its salience via the existing `record_state` (a legitimate state-change). **No delete, no new `status` value** —
  `page.py`'s `status: Literal["provisional","registered"]` and the whole frozen core stay byte-unchanged.
- **(e) Quarantine = report + a reusable filter API + a guard test:** `partition_canonical(index) →
  (registered, provisional)` is the seam future canonical projections (4-5, layer rollup) call; the excluded
  provisionals are surfaced as `confidence-capped` quarantine entries; and a guard test locks the invariant that a
  provisional/off-registry finding cannot move the frozen DMI/SMI.
- **(f)** No new wiki-log event kind (`log.py`'s `LogEvent.kind` Literal is frozen and has no
  `promote`/`prune` value). The **`LifecycleReport` artifact + the page `status`/`lastUpdatedAsOf`** are the
  replayable audit trail — consistent with how `DedupReport`/`LintReport` already serve as provenance.

---

## 1. The lifecycle engine (the testable heart)

A new pure module **`gpu_agent/wiki/lifecycle.py`** (additive, mirrors `wiki/lint.py`). It **reads** the store and
4-4b's `stale` signal and returns a `LifecycleReport`; it **mutates nothing** unless the caller passes `--apply`,
and then only through **existing** `WikiStore` methods.

```python
def promotion_candidates(store: WikiStore, config: LifecycleConfig) -> list[PromotionCandidate]: ...
def prune_candidates(store: WikiStore, stale: list[StaleEntry]) -> list[PruneCandidate]: ...
def partition_canonical(index: list[IndexEntry]) -> tuple[list[IndexEntry], list[IndexEntry]]: ...  # (registered, provisional)
def lifecycle(store, *, as_of, stale, config=DEFAULT_LIFECYCLE_CONFIG) -> LifecycleReport: ...       # assemble (propose)
def apply_lifecycle(store, report: LifecycleReport, *, as_of) -> AppliedSummary: ...                 # the --apply path
```

- **Reads only** (propose path): `store.index()`, `store.observations(pid)`, `store.findings.get(fid)`,
  `store.get_page(pid)`, and the `stale` list from `lint(store, as_of).health.stale` (4-4b).
- **Writes only via existing methods** (apply path): `update_header(pid, as_of=…, status="registered")` for
  promotions; `record_state(pid, …, salience=floor)` for prunes. Both already exist and are idempotent-safe.

---

## 2. Promotion (propose; persist + corroborate)

For each **provisional** page (`status == "provisional"`), of any `type`:
- **`persistence(store, pid)`** = the number of **distinct `asOf`** values among `store.observations(pid)`.
- **`corroboration(store, pid)`** = the number of **distinct `evidence.source`** values across all findings observed
  on the page (`observations → findings.get → finding.evidence → e.source`).
- A page is a **`PromotionCandidate`** iff `persistence ≥ config.min_persist_cycles` **and**
  `corroboration ≥ config.min_sources` (defaults 2 and 2). The candidate records `persistCycles`,
  `distinctSources`, and a human `verdict` (e.g. `"persisted 3 cycles, 2 sources → promote"`).
- Registered pages are skipped (already canonical). Provisional pages that miss either bar stay provisional and are
  **not** listed as candidates (but their near-miss is countable — see §5 "nothing silent").
- **`--apply`** flips each candidate to `status="registered"` via `update_header` (idempotent: a page already
  registered is a no-op). This is the charter's "reviewed → promoted" step, gated behind the flag.

---

## 3. Pruning (non-destructive)

Pruning is the reverse of promotion — a provisional candidate that **fizzled**:
- A **`PruneCandidate`** is a page that is **both `status == "provisional"` AND `stale`** in 4-4b's
  `lint(store, as_of).health.stale` (i.e. `effective_salience < stale_threshold` after decay). Registered pages
  that go quiet are **never** pruned — they are established coverage; only unpromoted provisionals are pruned.
- The reason string carries the stale detail (e.g. `"stale: eff_salience 0.04 < 0.1, quiet 3 cycles"`).
- **`--apply`** floors the page's salience via `record_state(pid, …, salience=config.prune_salience_floor)`
  (default 0.0), which is a legitimate `state-change` (keeps state/trajectory, just fades salience). **No page is
  deleted and no new status is introduced** — the page remains in the store, replayable, simply faded so 4-5 drops
  it from the brief. (A future "archived" status would be a deliberate `page.py` schema change — deferred.)

---

## 4. Quarantine (filter API + report + guard)

"Provisional never feeds canonical" (Part 18). Concretely:
- **`partition_canonical(index) → (registered, provisional)`** — a pure helper over `store.index()` that splits
  pages by `status`. This is the reusable **filter seam** any canonical projection (4-5's brief, the future layer
  rollup) calls to include only `registered` pages and treat `provisional` ones as candidates.
- The `provisional` half is surfaced in the report as **`QuarantineEntry`** rows (`pageId`, `status`,
  `confidenceCapped=True`, `note="not yet in coverage"`) — the metadata 4-5 renders as "provisional —
  confidence-capped."
- **Guard test (invariant lock):** a test proving that a **provisional / off-registry** finding cannot move the
  **frozen** DMI/SMI — the scorecard is built from gated findings via the frozen scorer, and off-registry
  `indicatorId`s carry no registry weight, so the invariant already holds structurally; the test locks it so a
  future change can't silently break quarantine.

---

## 5. The `LifecycleReport` (models; nothing silent)

```python
class PromotionCandidate(BaseModel):
    pageId: str
    type: str                       # "entity" | "theme"
    title: str
    persistCycles: int
    distinctSources: int
    verdict: str                    # e.g. "persisted 3 cycles, 2 sources -> promote"

class PruneCandidate(BaseModel):
    pageId: str
    type: str
    reason: str                     # e.g. "stale: eff_salience 0.04 < 0.1"

class QuarantineEntry(BaseModel):
    pageId: str
    status: str                     # always "provisional" here
    confidenceCapped: bool = True
    note: str = "not yet in coverage"

class LifecycleReport(BaseModel):
    asOf: str
    promotions: list[PromotionCandidate] = []
    prunes: list[PruneCandidate] = []
    quarantined: list[QuarantineEntry] = []
    provisionalConsidered: int = 0   # every provisional page was examined (nothing silent)

class LifecycleConfig(BaseModel):
    min_persist_cycles: int = 2
    min_sources: int = 2
    stale_threshold: float = 0.1     # reuses 4-4b's stale definition
    prune_salience_floor: float = 0.0

class AppliedSummary(BaseModel):     # returned by apply_lifecycle (the --apply path)
    promoted: int = 0
    pruned: int = 0
```

Every provisional page is examined and appears as a `QuarantineEntry`, so **`provisionalConsidered == len(quarantined)`**;
`promotions` and `prunes` are annotations on subsets of those same provisional pages (a promotion candidate is still
provisional — hence still quarantined — until an `--apply` run registers it). The report therefore accounts for
**every** provisional page (Part 29). The `LifecycleReport` + the page `status` / `lastUpdatedAsOf` are the replayable
audit trail (Part 20); re-running propose on an unchanged store is a pure no-op.

---

## 6. CLI wiring (additive) — `wiki-lifecycle`

A new subcommand (mirrors `wiki-lint`/`wiki-dedup`), no existing subcommand edited:

```
wiki-lifecycle --store DIR --as-of D [--apply] [--report R]
```
- Computes `stale` via `lint(store, as_of)` (4-4b), runs `lifecycle(...)`, prints/writes the `LifecycleReport`.
- **Without `--apply`:** propose-only — prints the report (promotions/prunes/quarantine counts + lists); mutates
  nothing.
- **With `--apply`:** flips promotion candidates to `registered` (`update_header`) and floors prune candidates'
  salience (`record_state`); prints an applied summary (`promoted N, pruned M`). Idempotent — a second `--apply`
  run over an unchanged store promotes/prunes nothing new.

---

## 7. Frozen vs additive (Part 33)

- **Byte-unchanged (frozen):** `gpu_agent/gate.py`, `scoring.py`, `registry/indicators.py`/`validate.py`, the
  `Finding` schema, the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, `store.py`
  (`JsonStore`/`FindingStore`), **every member of** `gpu_agent/wiki/store.py`/`log.py`/`page.py`/`ingest.py`/
  `lint.py`, and `gpu_agent/gathering/ingest.py`/`dedup.py`. 4-4c only *reads from* or *calls* these; it never edits
  them. In particular it introduces **no new `LogEvent.kind`** and **no new `status` value**.
- **Additive:** the new module `gpu_agent/wiki/lifecycle.py` (the engine + models + `LifecycleConfig`); the
  `wiki-lifecycle` subparser/handler/dispatch in `cli.py`. **No new dependency** (pydantic + stdlib).
- **Reuses, does not rebuild:** `WikiStore.observations`/`index`/`update_header`/`record_state`; 4-4b's `lint()`
  `stale` signal; the frozen finding-driven scorer (untouched — the quarantine guard just proves the invariant).

---

## 8. Doctrine

Code manages lifecycle-mechanics; the brain still curates (unchanged, frozen). **Nothing silent** (Part 29): every
promotion candidate, prune candidate, and quarantined page is counted and listed; `provisionalConsidered` proves
every provisional page was examined. **Propose-don't-auto-promote** (Part 18/16): status flips only behind the
explicit `--apply` review gate. **Provisional never drives canonical** (Part 18): the quarantine filter + the guard
test. **Replayable** (Part 20): the `LifecycleReport` + page `status`/`lastUpdatedAsOf`; no wall-clock; `as_of`
injected; re-run is a no-op. **Numbers only from gated findings** (Part 17): the engine reads finding evidence and
page metadata; it writes no number to any scorecard/index. **Pruning is non-destructive** (no data loss).

---

## 9. The 4-4c → later-discovery seam

4-4c ships the **lifecycle** over provisional pages that already exist. The deferred **discovery half** will *create*
new provisional topics (brain-driven theme / off-registry-entity threads from 4-4d's NEW candidate stream, an
`explore` budget, bounded rabbit-holing). Because 4-4c is **page-type agnostic** and reads only `status`, the moment
the discovery half starts writing provisional `theme` pages, promotion/pruning/quarantine apply to them for free —
no rework. Clean boundary: **the discovery half *opens* provisional threads; 4-4c *promotes, prunes, and quarantines*
them.**

---

## 10. Test strategy (deterministic; committed-fixture / built-via-API pattern)

- **Promotion:** `persistence` counts distinct `asOf` (not raw observation count); `corroboration` counts distinct
  evidence sources; threshold boundaries (exactly-min promotes; min-1 does not); registered pages skipped;
  page-type-agnostic (a theme page built via the store API promotes on the same rule).
- **Pruning:** a provisional+stale page is a candidate; a **registered**+stale page is **not**; a provisional
  fresh page is not.
- **Quarantine:** `partition_canonical` splits registered vs provisional; the guard test proves a provisional/
  off-registry finding leaves DMI/SMI unchanged.
- **`--apply`:** promotes/prunes exactly the candidates; a second run is a no-op (idempotent); the propose path
  mutates nothing (page files byte-identical before/after a no-apply run).
- **CLI:** `wiki-lifecycle` end-to-end via `main()` — propose prints the report; `--apply` changes status/salience
  and reports the summary.
- **Guards:** frozen-contract `git diff` empty (incl. all wiki modules + `gathering`); committed fixtures
  byte-unchanged; the full suite stays green (baseline **357 passed, 3 skipped** + the new tests).

---

## 11. Out of scope (deferred)

- **The brain-driven discovery step** — theme-page *creation*, the `explore` budget, off-registry topic definition,
  bounded rabbit-holing → a later sub-project (the discovery half).
- **A real "archived"/"pruned" `status`** and a store delete/prune method → would unfreeze `page.py`/`store.py`;
  deferred (non-destructive salience floor is enough; 4-5 fades faded provisionals).
- **A `promote`/`prune` `LogEvent.kind`** → would unfreeze `log.py`; the `LifecycleReport` + page status are the
  provenance.
- **Confidence-cap *rendering*** of provisionals → 4-5 (4-4c only carries the `confidenceCapped` metadata flag).
- **Auto-applied promotion without review** → explicitly rejected (propose-don't-auto-promote).

---

## 12. Acceptance (4-4c)

1. **Promotion:** a provisional page observed across ≥`min_persist_cycles` distinct cycles AND citing ≥`min_sources`
   distinct evidence sources is proposed for promotion; `--apply` flips it to `registered` idempotently; a page
   missing either bar is not proposed. Nothing is auto-promoted without `--apply`.
2. **Pruning:** a provisional+`stale` page is proposed for prune; `--apply` floors its salience non-destructively;
   a registered+stale page is never pruned; no page is deleted and no new status/log-kind is introduced.
3. **Quarantine:** `partition_canonical` cleanly splits registered vs provisional; a guard test proves a provisional/
   off-registry finding cannot move the frozen DMI/SMI; every provisional page is surfaced as a confidence-capped
   quarantine entry.
4. **Nothing silent / replayable:** the `LifecycleReport` counts + lists every promotion/prune/quarantine and
   accounts for every provisional page (`provisionalConsidered`); the report + page `status`/`lastUpdatedAsOf` make
   the cycle replayable; propose is a pure no-op on an unchanged store.
5. **Frozen contract intact** (incl. all wiki modules + `gathering` byte-unchanged; no new `status` value, no new
   `LogEvent.kind`); **additive only**; no new dependency; the full suite stays green.
6. **Feeds the sequence:** registered pages become 4-5's canonical coverage; provisional pages render as
   "not yet in coverage / confidence-capped"; the engine is page-type agnostic so the deferred discovery half's
   theme pages get lifecycle for free.
