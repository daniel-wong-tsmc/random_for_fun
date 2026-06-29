# Brain ingest into the wiki (sub-project 4-4a) — design

- **Date:** 2026-06-29
- **Status:** Draft for review (the first piece of sub-project 4-4 — the keystone writer)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md)
  (§4.6 "the brain curates the wiki", §4.2 the store interface); charter **Part 4** (memory & temporal
  judgment), **Part 8/26** (fetched/curated text is DATA not instructions), **Part 17** (numbers only from
  gated findings), **Part 20** (replayable), **Part 29** (nothing silent), **Part 38** (code emits the prompt,
  the agent reasons, code gates the result). Builds additively on **4-1** (the wiki/finding store).
- **Depends on:** 4-1 (merged — `WikiStore`/`FindingStore`). **Feeds:** 4-4b (materiality/lint reads the
  ingested updates + the `ingest`/contradiction signal), 4-4c (discovery builds on the same writer), 4-5 (the
  brief renders the curated pages + `diff`).

---

## 0. What 4-4a is — and the decomposition that scopes it

Sub-project **4-4** ("daily gather + scrape + relevance/lint + brain ingest + discovery engine") is the
largest piece of sub-project 4, spanning several independent subsystems. It is decomposed into a sequence,
each its own spec → plan → SDD → merge:

- **4-4a (this spec) — Brain ingest into the wiki:** the keystone *writer* that turns the day's gated findings
  into living entity pages. Makes 4-1's store and 4-3's Outlook finally do something.
- **4-4b — Relevance engine:** the multi-factor materiality / `lint` score + salience **decay** (reads what
  4-4a wrote; ranks what the daily `diff` surfaces).
- **4-4c — Discovery lane:** explore budget on the assignment; **theme pages** + provisional off-registry
  topics; quarantine from canonical; promotion on persist+corroborate (the Part 10 signal test).
- **4-4d — Daily gather mode + numeric scrape sweep + dedup-vs-store:** the input firehose (honest sourcing).

**4-4a ships the ENTITY-PAGE WRITER only.** It is NOT: the materiality score / salience decay (4-4b); theme
pages, the explore budget, provisional discovery, quarantine, or promotion (4-4c); the gather/scrape (4-4d).

**Locked decisions (from brainstorming):**
- **Hybrid: code routes, brain enriches.** A deterministic Phase 1 (code) guarantees every gated finding lands
  on its entity page; a brain Phase 2 (the `--emit-prompt`→`--recorded` seam) enriches those pages.
- **Phase 1 routes on `finding.entity` only, idempotently.** Themes are emergent topics → 4-4c.
- **Phase 2 enriches existing entity pages only** (no page creation by the brain in 4-4a).
- **Contradictions are recorded but not yet weighted** (the materiality model is 4-4b).
- **Salience is brain-set here; decay is 4-4b.**

---

## 1. The CLI seam

A new subcommand **`wiki-ingest`** (distinct from the existing `ingest`, which is blobs→RawDocuments). It takes
the day's gated findings, the store root, and `--as-of`, and runs in two phases on one invocation (mirroring the
`extract`/`judge` flag style):

```
# Phase 1 only (deterministic backbone; no brain):
cli wiki-ingest --findings findings.json --store store/ --as-of 2026-06-29

# Phase 1 + emit the Phase-2 bundle for the Opus subagent (no brain call here):
cli wiki-ingest --findings findings.json --store store/ --as-of 2026-06-29 --emit-prompt
#   (the subagent answers -> ingest-answer.json)

# Phase 1 (idempotent no-op) + apply the brain's enrichment:
cli wiki-ingest --findings findings.json --store store/ --as-of 2026-06-29 --recorded ingest-answer.json
```

- `--findings` points at a gated-findings JSON (a list of `Finding`, e.g. a scorecard's `findings` or a
  `findings.json`). Each is appended to `FindingStore` (idempotent) so `append_observation` can gate it.
- `--category` is an optional flag (e.g. `chips.merchant-gpu`) used as the `category` on auto-created entity
  pages (for index/diff grouping); defaults to `None` when omitted.
- **Phase 1 always runs first**, even under `--emit-prompt`. Unlike `extract`/`judge` (pure prints), the
  deterministic backbone should always land; it is idempotent, so re-running under `--recorded` is a no-op. The
  *brain prompt* stays pure (the bundle is just printed); the deterministic substrate is allowed to run.
- With neither flag → Phase-1-only (graceful degradation / tests).

---

## 2. Phase 1 — deterministic routing (code)

For each gated finding (in input order):
1. Resolve `pid = "entity:" + slug(finding.entity)` where `slug` lowercases and replaces non-`[a-z0-9]+` runs
   with `-` (e.g. `"NVDA"` → `entity:nvda`, `"SK hynix"` → `entity:sk-hynix`).
2. Append the finding to `FindingStore` (idempotent; identical re-append is a no-op, differing content on a
   reused id fails loud — existing 4-1 behavior).
3. If `pid` is absent, `create_page(pid, "entity", title=finding.entity, category=<the --category flag or None>,
   as_of=as_of)` (default `status="provisional"`).
4. If `finding.id` is **not** already in `observations(pid)`, `append_observation(pid, finding.id, as_of=as_of)`;
   otherwise skip (idempotent).

**Fail-loud:** a finding with a missing/empty `entity` cannot be routed → raise (never silently dropped, Part 29).
**Returns** the set of touched page ids (for the Phase-2 bundle).

Phase 1 is a pure function of `(findings, store, as_of)` — re-running the same day adds no new observations or
log events.

---

## 3. Phase 2 — brain enrichment (the emit-prompt → recorded seam)

### 3.1 The bundle (`--emit-prompt`)

Prints `{system, schema, asOf, pages}` (no brain call). `system` = a new `INGEST_SYSTEM` prompt instructing the
brain to curate each entity page from its standing thesis + the day's new findings (cite finding ids in the
prose; never invent numbers; flag a contradiction when a new finding opposes the page's current state). `schema`
= `IngestResult.model_json_schema()`. `pages` = one entry per **touched** entity page:

```json
{ "pageId": "entity:nvda", "title": "NVDA",
  "currentState": "...", "currentTrajectory": "...", "currentSalience": 0.0,
  "currentCrossRefs": [...], "currentBody": "<markdown>",
  "newFindings": [ { "id": "f-...", "statement": "...", "why": "...",
                     "impact": {...}, "evidence": [...] } ] }
```

### 3.2 The brain's answer — `IngestResult`

```python
class PageEnrichment(BaseModel):
    pageId: str                  # MUST be an existing entity page (Phase 1 created it)
    bodyMarkdown: str            # curated prose; claims cite finding ids
    state: str                   # e.g. "accelerating"
    trajectory: str              # e.g. "on-track -> slipping"
    salience: float              # brain-set priority (decay is 4-4b)
    crossRefs: list[str] = []    # other entity page ids
    contradictsThesis: bool = False
    contradictionNote: str = ""

class IngestResult(BaseModel):
    pages: list[PageEnrichment]
```

### 3.3 The applier (`--recorded`) — deterministic, gated

For each `PageEnrichment` (Phase 1 has already run):
- **Reject loud** if `pageId` does not exist (the brain may only enrich Phase-1 pages; no page creation in
  4-4a — themes/new topics are 4-4c) or is not an `entity:` page.
- `set_body(pageId, bodyMarkdown, as_of=as_of)` — **new additive `WikiStore` method** (today the body is only
  writable at `create_page`). Skips the write if the body is unchanged.
- `record_state(pageId, state=..., trajectory=..., salience=..., as_of=as_of)` — **only if** state, trajectory,
  or salience differs from the page's current values (applier-level idempotency, so re-running a day logs no new
  `state-change`). The existing 4-1 `record_state` is untouched.
- `update_header(pageId, crossRefs=...)` — only if `crossRefs` changed.
- After all pages: append **one** `ingest` `LogEvent` for the run (kind already declared in 4-1), with a
  `detail` summarizing pages enriched and any `contradictsThesis` notes. **The contradiction is recorded, not
  yet weighted** — the multi-factor materiality model (contradiction = highest) is 4-4b.

Re-running `--recorded` with the same answer is a no-op (body/state unchanged → skipped; one `ingest` event is
the only thing that could repeat — make it idempotent by skipping if an identical `ingest` event for that
`asOf` already exists).

---

## 4. The new `WikiStore.set_body` method (additive)

```python
def set_body(self, page_id, body, *, as_of) -> WikiPage:
    """Replace a page's curated markdown body, bumping lastUpdatedAsOf. Raises PageNotFound.
    No log event (body edits are not temporal observations; the ingest event covers the run)."""
```

Reuses the existing `_read`/`_write` helpers; leaves the header otherwise unchanged except `lastUpdatedAsOf`.
All other 4-1 `WikiStore` methods stay byte-unchanged.

---

## 5. Frozen vs additive (Part 33)

- **Byte-unchanged:** `gate.py`, `scoring.py`, `registry/indicators.py`/`validate.py`, the `Finding` schema, the
  6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, the existing `JsonStore`, and the existing
  4-1 `WikiStore`/`WikiLog`/`WikiPage`/`FindingStore` members (4-4a only *adds* `set_body`).
- **Additive:** `WikiStore.set_body`; a new module `gpu_agent/wiki/ingest.py` (Phase-1 router, Phase-2 applier,
  `IngestResult`/`PageEnrichment`, the bundle builder, `INGEST_SYSTEM`); the `wiki-ingest` CLI subcommand.
- **Reuse, do not rebuild:** `FindingStore.append/exists/get`; `WikiStore.create_page/append_observation/
  record_state/update_header/observations/get_page`; the `--emit-prompt`/`--recorded` seam + `RecordedClient`
  pattern from `extract`/`judge`.

---

## 6. Doctrine

Every finding is gated through `FindingStore` before it lands (numbers only from gated findings, Part 17). The
brain curates prose/state/trajectory/salience but invents no measured values; the curated body is DATA, not
instructions (Part 8/26). The `ingest` log event + idempotent re-runs make every day **replayable** (Part 20).
Nothing silent (Part 29): an unroutable finding (missing/empty `entity`) fails loud; a brain op targeting a
non-existent or non-entity page is rejected loud; an ungated finding never lands (`append_observation` gates on
`FindingStore`).

---

## 7. Test strategy (deterministic; committed-fixture pattern)

- **Phase 1 (no brain):** `slug` normalization; route creates entity pages + appends observations; re-running
  the same `asOf` adds **no** new observations or log events (idempotency); a finding with empty `entity` raises;
  an ungated finding cannot land (gated by `FindingStore`).
- **`set_body`:** replaces the body, bumps `lastUpdatedAsOf`, leaves the header otherwise intact; `PageNotFound`
  on a missing page; unchanged-body write is skipped.
- **Phase 2 applier** via a committed `fixtures/recorded/ingest-*.json` `IngestResult`: applies `set_body`,
  `record_state` (and **skips** when unchanged), `crossRefs`, and logs exactly one `ingest` event with the
  contradiction note; an op for a missing/non-entity page is rejected loud; re-applying the same answer is a
  no-op.
- **`--emit-prompt`** prints a well-formed bundle (touched pages with header+body+newFindings; valid schema).
- Frozen-contract git-diff guard (byte-unchanged) + full suite green (baseline after 4-3: **282 passed,
  3 skipped**, plus the new tests).

---

## 8. Out of scope (later 4-4 pieces / arcs)

- The materiality / `lint` **score**, the salience **decay**, and the daily-`diff` surfacing rank (4-4b).
- Theme pages, the `explore` budget on the assignment, provisional off-registry discovery, quarantine from
  canonical, and promotion on persist+corroborate (4-4c).
- The daily gather mode, the numeric **scrape sweep** (e.g. `gpuSpotPrice`), and cross-run dedup-vs-store (4-4d).
- The 4-5 brief render of the curated pages.

---

## 9. Acceptance (4-4a)

1. `wiki-ingest` Phase 1 routes every gated finding to its `entity:<slug>` page (auto-create; idempotent);
   re-running the same `asOf` adds no new observations or log events; an unroutable finding fails loud.
2. `--emit-prompt` prints a bundle of the touched pages (header + body + new findings) against the
   `IngestResult` schema; no brain is called.
3. `--recorded` applies an `IngestResult`: `set_body`, idempotent `record_state`, `crossRefs`, and exactly one
   `ingest` log event carrying any contradiction note; a brain op targeting a missing or non-entity page is
   rejected loud; the brain creates no pages.
4. `WikiStore.set_body` is added (additive); every existing 4-1 `WikiStore`/`WikiLog`/`WikiPage`/`FindingStore`
   member is byte-unchanged; the frozen contract is byte-unchanged.
5. Full suite green; deterministic + replayable (numbers only from gated findings; nothing silent).
