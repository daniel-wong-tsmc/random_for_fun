# Daily gather mode + numeric scrape sweep + cross-run dedup-vs-store (sub-project 4-4d) — design

- **Date:** 2026-07-01
- **Status:** Draft for review (the input firehose of sub-project 4-4 — **reordered ahead of 4-4c**)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md)
  (§1.4 "noise control is the product", §3 row 4-4, §4.5); charter **Part 37** (the gathering swarm /
  follow-the-trail with brakes), **Part 22** (source inventory; honest sourcing — paywalled labeled `estimate`,
  never scraped), **Part 17** (numbers only from gated findings), **Part 20** (replayable snapshots), **Part 29**
  (nothing silent), **Part 38** (running the swarm in Claude Code). Builds additively on **4-1** (the store /
  `FindingStore`), **4-2** (the `cadence × horizon` tags + `sourceInventory`), **4-4a** (the `wiki-ingest` writer),
  **4-4b** (the materiality / lint engine), and the existing **Part-37 ingest seam** (`gather/../gathering/ingest.py`
  `normalize_documents`).
- **Depends on:** 4-1 (`WikiStore`/`FindingStore`), 4-2 (`IndicatorHorizons` cadence tags; `sourceInventory`),
  4-4a (`wiki-ingest` entity routing), the existing `normalize_documents` (within-run URL dedup + tier stamping)
  and the `gather-category`/`run-cycle` skills. **Feeds:** **4-4c** (the discovery lane — consumes 4-4d's de-noised
  fresh stream + its NEW-thread candidates as the raw material for provisional off-registry discovery) and **4-4b**
  (an UPDATE finding becomes a material move) and the daily brief (4-5).

---

## 0. What 4-4d is — the reorder, and the decomposition that scopes it

Sub-project **4-4** ("daily gather + scrape + relevance/lint + brain ingest + discovery engine") is decomposed
into a sequence, each its own spec → plan → SDD → merge:

- **4-4a (done, merged) — Brain ingest into the wiki:** the keystone *writer* (gated findings → entity pages).
- **4-4b (done, merged) — Relevance engine / the wiki `lint`:** materiality score + salience decay + structural health.
- **4-4d (this spec) — Daily gather mode + numeric scrape sweep + cross-run dedup-vs-store:** the **input firehose**
  that reliably brings in fresh material and — because *noise control is the product* (umbrella §1.4) — **surfaces
  only what changed, logging the rest.**
- **4-4c — Discovery lane:** explore budget; theme pages + provisional off-registry topics; quarantine; promotion
  on persist+corroborate (Part 10). *Consumes* 4-4d's de-noised stream + NEW candidates.

**Reorder (decided this session):** the umbrella order was 4-4a→4-4b→4-4c→4-4d, but **4-4d is now built before
4-4c**. Rationale: 4-4c is the *brain discovery + lifecycle* lane (4-4b spec §11) and "noticing the off-list topic"
needs **gathered raw material to notice from** — which is exactly what 4-4d produces. Building the firehose first
gives 4-4c real, de-noised live input instead of a stub. New order: **4-4a → 4-4b → 4-4d → 4-4c → 4-5.**

**Locked decisions (from brainstorming):**
- **Full firehose (all three pieces).** Daily gather mode **and** the numeric scrape sweep **and** cross-run
  dedup-vs-store, in one sub-project.
- **Hybrid two-layer dedup.** **L1** (pre-brain, doc-level): drop a gathered `RawDocument` whose normalized URL or
  content-hash is already in a persistent **seen-document index** (saves extraction cost). **L2** (post-gate,
  finding-level): classify each gated `Finding` against the store's latest vintage for `(entity, indicatorId)` into
  **NEW / UPDATE / DUPLICATE**. NEW+UPDATE flow to ingest; DUPLICATE is logged and dropped (no re-observation).
- **The numeric scrape rides the frozen brain.** A daily numeric (e.g. `gpuSpotPrice`) reaches the store as a
  **gatherer snapshot → the FROZEN `extract → gate` → a measured `Finding`** (value + receipt, secondary tier,
  confidence-capped). **No code writes a number directly** (Part 17 intact; single gate checkpoint; replayable). A
  standalone non-session code fetcher stays deferred (Part 37).
- **L1's memory is a new persistent seen-document index** (URL/hash → first-seen `asOf`), not derived from stored
  findings' evidence URLs (which would miss documents that produced no finding).
- **L2's "changed" test is tolerance-based** (a numeric value delta beyond a relative tolerance, or a magnitude
  change; for observed/qualitative findings, a normalized-statement or trend/magnitude change).
- **One 4-4d spec, one branch.** The pure-code dedup core is built + tested via subagent-driven-development
  (pytest); the daily-gather-mode + scrape skill edits are validated by documented dry-runs — mirroring the existing
  split (`normalize_documents` is code; `gather-category` is a skill).

**4-4d ships the FIREHOSE only.** It is NOT: theme pages / the explore budget / provisional off-registry discovery /
quarantine / promotion / pruning (4-4c); a standalone non-session web fetcher or hard multi-source corroboration
(Part 37 deferred); unattended scheduling (Part 28); the brief render (4-5).

---

## 1. The cross-run dedup-vs-store engine (the testable heart)

A new pure module **`gpu_agent/gather/dedup.py`** with two independent, deterministic layers and one report.

```python
def filter_seen_documents(docs: list[RawDocument], index: SeenDocIndex, *, as_of: str
                          ) -> tuple[list[RawDocument], list[DroppedDoc]]: ...   # L1
def classify_findings(findings: list[Finding], store: WikiStore, *, config: DedupConfig
                      ) -> DedupResult: ...                                        # L2
```

- **Reads only:** the `SeenDocIndex` (L1) and the `WikiStore` entity-page observations + `FindingStore.get` (L2).
  It **writes no page and no number** — it *classifies and routes* (Part 17). DUPLICATEs are logged, never written.
- Returns a **`DedupReport`** (§4) so **nothing is silent** (Part 29).

---

## 2. L1 — the seen-document index (pre-brain, doc-level)

The Part-37 `normalize_documents` already de-dups **within a run** by normalized URL and stamps tiers. L1 adds
**cross-run** memory so a document already seen on an earlier day is not re-extracted.

- **`SeenDocIndex`** — a persistent, append-only index keyed by **normalized URL** *and* **content-hash**
  (`sha256` of the normalized content), each mapping to the **first-seen `asOf`**. Lives in the gitignored runtime
  store (e.g. `store/seen_docs.jsonl`, sibling to `wiki/` and `findings/`), like the rest of the store (Part 9).
- **`filter_seen_documents`** runs on the output of `normalize_documents`: for each `RawDocument`, if its normalized
  URL **or** its content-hash is already in the index → **drop as known** (recorded in the `DedupReport`); otherwise
  keep it **and record** (url, hash, first-seen `as_of`) in the index. URL-match catches a re-fetch of the same
  page; content-hash catches **the same content re-published at a new URL**.
- L1 is **pre-brain** — dropped docs never reach `extract`, saving the brain call. Idempotent: re-running a cycle
  finds every doc already indexed → all dropped.

---

## 3. L2 — the finding-level classifier (post-gate, pre-ingest)

After `extract → gate` produces this cycle's gated `Finding`s (and **before** `wiki-ingest`), L2 classifies each
against what the store already knows, so a re-reported known fact does not become a redundant observation.

- **The prior-vintage lookup (frozen-safe):** `FindingStore` exposes only `get`/`exists`/`append` (no iteration),
  so L2 reads priors through the **wiki**: for a finding on entity *E*, resolve its entity page id
  `entity:<slug(E)>` (reusing `wiki/ingest.slug`), read `WikiStore.observations(pageId)`, `findings.get` each, and
  keep those with the same `indicatorId`. The **latest vintage** among them is chosen by the *same* collapse the
  frozen `dmi_smi_contribution` uses: max by `(capturedAt, observedAt, magnitude)`. (Entity pages are the canonical
  dedup surface because 4-4a routes every finding to `entity:<slug(entity)>`. When 4-4c later adds theme pages, the
  entity key still holds — every finding carries an `entity`.)
- **Classification** of a fresh finding *f* for `(entity, indicatorId)`:
  - **NEW** — no prior vintage on the page (page absent, or no observation with that `indicatorId`). → **ingest**
    (opens/extends the thread).
  - **UPDATE** — a prior vintage exists **and *f* changed beyond tolerance** (§3.1). → **ingest** (a material move;
    4-4b scores it).
  - **DUPLICATE** — a prior vintage exists **and *f* is unchanged within tolerance**. → **logged + dropped**, no
    re-observation.
- **Intra-batch collapse:** if this cycle's fresh batch contains several findings for the same
  `(entity, indicatorId)`, they are first collapsed to their own latest vintage (the same tie-break) before
  classification, so one cycle contributes at most one NEW/UPDATE per key and the rest are DUPLICATEs — the
  comparison is always *this cycle's best reading* vs *the store's prior vintage*.
- L2 returns the partition (`new`, `update`, `duplicate`) inside the `DedupResult`; the caller ingests
  `new + update` via the existing 4-4a `wiki-ingest` path and logs the `duplicate` count.

### 3.1 The "changed" test (tolerance-based, tunable — `DedupConfig`)
- **Measured findings** (a `value.number`): **UPDATE** iff `abs(new - prior) > rel_tol * max(abs(prior), eps)` **or**
  the `magnitude` changed; else **DUPLICATE**. Default `rel_tol = 0.01` (1%), `eps = 1e-9`.
- **Observed / qualitative findings** (no numeric `value`): **UPDATE** iff the **normalized `statement`** changed
  (case/whitespace-folded) **or** the `trend`/`magnitude` changed; else **DUPLICATE**.
- All thresholds live in a small **`DedupConfig`** (a pydantic model of constants, defaulted, overridable for
  tuning/tests), like 4-4b's `LintConfig`.

---

## 4. The `DedupReport` (provenance; nothing silent)

```python
class DroppedDoc(BaseModel):
    url: str
    reason: str                    # "seen-url" | "seen-content-hash"
    firstSeenAsOf: str

class FindingClass(BaseModel):
    findingId: str
    entity: str
    indicatorId: str
    verdict: str                   # "new" | "update" | "duplicate"
    priorFindingId: Optional[str] = None
    detail: str = ""               # e.g. "value 2.10 -> 2.35 (>1%)" or "unchanged within 1%"

class DedupReport(BaseModel):
    asOf: str
    docsSeen: int
    docsDroppedKnown: list[DroppedDoc] = []
    findingsNew: list[FindingClass] = []
    findingsUpdate: list[FindingClass] = []
    findingsDuplicate: list[FindingClass] = []
```

Printed / `--out` by the CLI and summarized in a log line. Every dropped doc and every DUPLICATE is **counted and
listed** — a daily sweep that drops 90% of its input as noise says so explicitly (Part 29). The `SeenDocIndex` +
the `RawDocument` snapshot + the `DedupReport` make the cycle **replayable** (Part 20).

---

## 5. CLI wiring (additive) — where the two layers plug in

The dedup plugs into the existing pipeline at exactly two seams; no existing stage is modified:

```
daily gather (skill) → blobs
  → normalize_documents            (within-run URL dedup + tier — EXISTS, unchanged)
  → L1 filter_seen_documents       (drop cross-run-known docs; update the seen index)   ← NEW
  → RawDocument snapshot → extract → gate → gated Findings
  → L2 classify_findings           (NEW/UPDATE → ingest; DUPLICATE → log+drop)          ← NEW
  → wiki-ingest [4-4a] → wiki-lint [4-4b]
```

Realized as an additive CLI surface (final shape settled in the plan; **no existing subcommand/handler edited**):
a `--dedup-store <dir>` option (+ `--dedup-out`) that turns on L1 on the `ingest`/normalize path and L2 on the
`wiki-ingest` path, or a small dedicated subcommand that composes them. The `DedupReport` is emitted to stdout / a
file.

---

## 6. Daily gather mode (skill; Part 37/38; dry-run validated)

A recency-windowed variant of the existing `gather-category` follow-the-trail loop (it is a **skill**, session-run,
validated by documented dry-runs — not pytest):

- **Recency window** — seed searches and the on-topic filter bias to the last *N* days (a dial), so the daily sweep
  is "what's new," not a full re-crawl.
- **Cadence-prioritized** — prioritizes **daily/weekly-cadence** indicators (read from the 4-2 `cadenceHorizon`
  tags) + recent news + the permissive numeric-scrape sources (§7).
- **Bounded** — the four Part-37 dials (max rounds, max docs, max fan-out, on-topic filter) tuned smaller for a
  daily cadence; **every cap that truncates is logged with what it skipped** (Part 29). Returns raw docs + candidate
  leads only (never Findings) — the single frozen-brain handoff is preserved.
- `run-cycle` gains a **daily invocation path** that threads the L1/L2 dedup wiring into the run.

---

## 7. Numeric scrape sweep (Part 22 honest; rides the frozen brain)

- The **permissive** daily numeric sources (e.g. GPU marketplaces for `gpuSpotPrice`, already inventoried in
  `sourceInventory` by 4-2) are ordinary **gatherer targets**: snapshot the page as a `RawDocument` → the **FROZEN**
  `extract → gate` → a **measured `Finding`** (value + url/source/date receipt; **secondary** tier;
  **confidence-capped**). No code path sets a number (Part 17); the value is auditable and the run replays from the
  snapshot (Part 20).
- **Part 22 boundary (hard):** paywalled / licensed sources (e.g. SemiAnalysis, TrendForce) stay **inventoried and
  labeled `estimate`, and are NEVER fetched** — the daily-mode skill logs them as a coverage gap, exactly as C's
  manifest-driven gather already does for paywalled sources.
- The scraped daily findings then ride the *same* L1/L2 dedup + `wiki-ingest` + `wiki-lint` path as any other
  finding (a daily price that hasn't moved beyond tolerance is a **DUPLICATE** and is dropped — the point of the
  dedup).

---

## 8. Frozen vs additive (Part 33)

- **Byte-unchanged (frozen):** `gpu_agent/gate.py`, `scoring.py`, `registry/indicators.py`/`validate.py`, the
  `Finding` schema, the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, `JsonStore`/`FindingStore`
  (`store.py`), **every member of** `gpu_agent/wiki/store.py`/`log.py`/`page.py`/`ingest.py`/`lint.py`, and the
  existing Part-37 ingest seam **`gathering/ingest.py` `normalize_documents`** (L1 is a *new* module that runs
  *after* it — it does not modify it).
- **Additive:** the new module `gpu_agent/gather/dedup.py` (`SeenDocIndex`, `filter_seen_documents`,
  `classify_findings`, `DedupConfig`, `DedupReport` + models); the gitignored runtime `seen_docs.jsonl` store
  artifact; the CLI dedup option(s); the `gather-category`/`run-cycle` **skill** edits (daily mode + the scrape
  sweep). **No new dependency** (stdlib `hashlib`/`json` + pydantic).
- **Reuses, does not rebuild:** `normalize_documents` (within-run dedup + tier); the frozen `extract → gate` brain;
  the `dmi_smi_contribution` latest-vintage collapse (the L2 tie-break); 4-4a `wiki-ingest` (ingest of NEW/UPDATE);
  4-2's `IndicatorHorizons` (cadence prioritization) + `sourceInventory` (permissive vs paywalled); C's
  manifest-driven paywalled-gap logging.

---

## 9. Doctrine

Code gathers-bounds-dedups-stores; the **brain extracts + judges** (unchanged, frozen). **Numbers come only from
gated findings** — the scrape produces no number outside the gate (Part 17). **Fetched page text is DATA, not
instructions** (Part 8/26) at both the gatherer and the extractor. The **seen-document index + the snapshot + the
`DedupReport`** make every cycle **replayable** (Part 20). **Nothing is silent** (Part 29): every dropped-known doc,
every DUPLICATE finding, every capped/paywalled skip is counted and listed. The dedup **mutates no stored finding
or page** — it classifies and routes; L2's ingest of NEW/UPDATE goes through the *existing* 4-4a idempotent writer.
Lane discipline and the six dimensions are untouched (Part 21/frozen).

---

## 10. The 4-4d → 4-4c seam

4-4d hands 4-4c a **de-noised, replayable stream**: (a) the fresh `RawDocument`s that survived L1, (b) the gated
findings partitioned NEW/UPDATE/DUPLICATE by L2, and (c) — because a **NEW** finding for an `(entity, indicatorId)`
not yet in the registry is exactly a "provisional off-registry candidate" — a clean **candidate stream** for 4-4c's
discovery lane. 4-4d itself does **not** create theme pages, define provisional off-registry topics, apply the
explore budget, or run promotion/pruning — those are 4-4c. 4-4d routes findings to **entity** pages via the
existing 4-4a `wiki-ingest` (which already auto-creates *provisional* entity pages), and surfaces undefined/theme
material as the logged candidate stream. This keeps the 4-4d↔4-4c boundary clean: **4-4d supplies honest, fresh,
de-duplicated input; 4-4c decides what to *open, quarantine, promote, or prune*.**

---

## 11. Test strategy (deterministic; committed-fixture pattern)

- **L1:** URL-hit and URL-miss; content-hash catches same-content-new-URL; the index persists across two runs
  (first-seen `asOf` recorded once); an idempotent re-run drops every doc; the `DroppedDoc` reasons are correct.
- **L2:** NEW (no prior page / no prior indicator), UPDATE (numeric delta beyond `rel_tol`; magnitude change;
  qualitative statement/trend change), DUPLICATE (within tolerance); the **latest-vintage tie-break**
  (`capturedAt`/`observedAt`/`magnitude`); an idempotent re-run of an unchanged cycle → **all duplicate**; the
  `DedupReport` counts sum to the input.
- **CLI:** end-to-end on committed fixtures — gather-fixture blobs → normalize → L1 → (recorded extract) → gate →
  L2 → ingest → the `DedupReport` is well-formed; re-run is a no-op.
- **Skills (dry-run, documented):** daily-mode recency window + cadence prioritization + caps-logged; the scrape
  sweep fetches only permissive sources and logs paywalled sources as gaps (never fetched).
- **Guards:** frozen-contract `git diff` empty (incl. `normalize_documents` + all wiki modules); committed fixtures
  byte-unchanged; the full suite stays green (baseline after 4-4b: **332 passed, 3 skipped**, plus the new tests).

---

## 12. Out of scope (deferred / later 4-4 pieces)

- **Theme pages, the explore budget, provisional off-registry lifecycle, quarantine, promotion/pruning** → 4-4c.
- **A standalone non-session code web fetcher** and **hard multi-source corroboration + a hard secondary-confidence
  cap** → deferred (Part 37).
- **Unattended daily scheduling** (Part 28).
- **The brief render** of the day's "what moved" → 4-5.
- **Semantic (embedding) dedup** — L2 is structural `(entity, indicatorId)` + tolerance, not semantic similarity.

---

## 13. Acceptance (4-4d)

1. **Cross-run dedup-vs-store:** L1 drops documents already seen in a prior cycle (URL **or** content-hash) *before*
   extraction and records new ones in a persistent seen-document index; L2 classifies each gated finding **NEW /
   UPDATE / DUPLICATE** against the store's latest vintage for `(entity, indicatorId)`; NEW+UPDATE are ingested,
   DUPLICATEs are logged and dropped; a `DedupReport` counts and lists everything — **nothing silent**.
2. **Idempotent:** re-running the same cycle drops every doc (L1) and classifies every finding DUPLICATE (L2) — no
   new observations.
3. **Daily gather mode:** a recency-windowed Part-37 loop prioritizes daily/weekly-cadence indicators + recent news
   + permissive scrape sources, bounded by the four caps (tuned + logged).
4. **Numeric scrape:** permissive daily sources snapshot → the FROZEN `extract → gate` → a measured, receipted,
   confidence-capped `Finding`; paywalled/licensed sources are labeled `estimate` and **never fetched** (Part 22).
5. **Frozen contract intact** (incl. `normalize_documents` + all wiki modules byte-unchanged); **additive only**; no
   new dependency; **numbers only from gated findings**; the full suite stays green.
6. **Feeds the sequence:** UPDATEs become 4-4b material moves; the de-noised stream + NEW candidates feed 4-4c.
