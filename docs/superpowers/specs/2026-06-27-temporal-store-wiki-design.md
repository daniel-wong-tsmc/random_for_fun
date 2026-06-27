# Temporal store + LLM-wiki thread model (sub-project 4-1) — design

- **Date:** 2026-06-27
- **Status:** Draft for review (the first piece of sub-project 4; the keystone)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** the sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md)
  and charter [`docs/agent-swarm-charter.md`](../../agent-swarm-charter.md) **Part 39** (sp4 decomposition),
  Parts 4 (memory & temporal judgment), 9 (storage & scoped query), 10 (the signal test), 17 (rating /
  numbers-only-from-gated-findings), 18 (discovery lane: provisional → promoted), 20 (replayability), 33
  (frozen vs additive), 34 (cold-start), 38 (harness doctrine).
- **Model for the temporal core:** Karpathy's "LLM wiki"
  (<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>) — a persistent, compounding markdown
  knowledge base of **pages** catalogued by an **index** and journalled by an append-only **log**.

---

## 0. What 4-1 is (and is not)

4-1 is the **keystone temporal store** everything else in sub-project 4 reads. It ships, as **pure,
fully-deterministic code**:

1. a standalone, append-only **`FindingStore`** — every gated `Finding` stored once, addressable by id
   (finishing Part 9's "append-only, versioned time-series of *every Finding*");
2. an **LLM-wiki `WikiStore`** — entity/theme **threads** as living markdown pages (a small code-owned
   frontmatter header + a brain-curated body), an append-only **`log.jsonl`** that is the temporal source of
   truth, a computed **`index`**, and the create / append / record-state / query / **`diff(asOf, prevAsOf)`**
   interface;
3. the **schemas** the two stores persist.

**4-1 is NOT** the daily gather, the dedup-vs-store pass, the multi-factor materiality / `lint` engine, the
salience-**decay** computation, or the **brain-driven ingest** (routing a finding to its page, writing the
prose body, flagging contradictions). Those are **4-4** (charter Part 39 — deferred by decision). 4-1 ships
the store primitives *as exactly the contract the 4-4 brain will call*, and is validated entirely by `pytest`
(no LLM, no skill).

**Locked decisions (from brainstorming; do not relitigate without reason):**
- Pages persist as **markdown + frontmatter**, one living `.md` per thread (truest to Karpathy; git-diffable).
- The frontmatter codec is a **no-new-dependency `key: <json.dumps(value)>` serializer** (JSON is a YAML-flow
  subset; we read it back with `json.loads`, so correctness depends only on the stdlib `json`). **No PyYAML.**
- The append-only **history** (which findings landed when; state transitions) lives in **`log.jsonl`**, *not*
  in the frontmatter — so the frontmatter stays small and a daily ingest produces clean diffs.
- Findings live **once** in a standalone `FindingStore`; pages reference them by id and resolve through it.
- 4-1 is **pure code store + `diff()` only**; brain ingest / lint / salience-decay are 4-4.

---

## 1. Module layout (all additive — nothing frozen is touched)

Mirrors the existing layout (flat stores in `store.py`; multi-file concerns get a package):

- **`gpu_agent/store.py`** — add `FindingStore` next to the existing `JsonStore`. `JsonStore` keeps persisting
  scorecards **byte-unchanged**; 4-1 reuses it as-is for the scorecard half of "persist scorecards *and* wiki
  pages."
- **`gpu_agent/wiki/`** (new package):
  - `page.py` — the `WikiPage` header model + the frontmatter serializer/parser + page file read/write.
  - `log.py` — the `LogEvent` model + the append-only `WikiLog` (read / append, deterministic `seq`).
  - `store.py` — `WikiStore`: the create / append / record-state / query / `diff` interface; the
    `WikiDiff` / `WindowView` / `IndexEntry` result types.
  - `__init__.py` — re-exports (`WikiStore`, `WikiPage`, `FindingStore` re-export optional).

No edits to `gate.py`, `scoring.py`, `registry/indicators.py`, `registry/validate.py`, the `Finding` schema,
the 6 dimension names, the rating scale, or `pipeline.py`'s Part-7 gate (charter Part 33 / Part 39 self-check).

---

## 2. The `FindingStore` (canonical, append-only) — `gpu_agent/store.py`

One gated `Finding` per file at `store/findings/<id>.json`. Mirrors `JsonStore`'s simplicity.

```python
class FindingNotFound(KeyError): ...

class FindingStore:
    def __init__(self, root: pathlib.Path): ...
    def append(self, finding: Finding) -> pathlib.Path: ...   # write-if-absent
    def get(self, finding_id: str) -> Finding: ...            # raises FindingNotFound
    def exists(self, finding_id: str) -> bool: ...
```

Rules:
- **Immutable + idempotent:** `append` writes only if the file is absent. If a file with that id already
  exists and its content is **identical**, `append` is a **no-op** (findings never change once gated). If it
  exists and **differs**, `append` **raises** (an id collision is a data-integrity bug → fail loud, per the
  charter "config/data errors fail loud").
- **Id safety:** a `finding.id` is validated against a filename-safe pattern (`[A-Za-z0-9._-]+`); anything
  else raises (no path traversal, no surprise filenames).
- **Read:** `get` raises `FindingNotFound` on a missing id; `exists` never raises.

This makes the wiki's "every page claim cites a **gated** finding" guarantee enforceable (see §4
`append_observation`).

---

## 3. The page = frontmatter header + markdown body — `gpu_agent/wiki/page.py`

One living `.md` per thread at `store/wiki/<type>/<slug>.md` (`type ∈ {entity, theme}`; `slug` = the id after
its `entity:` / `theme:` prefix; slug validated `[a-z0-9-]+`).

### 3.1 `WikiPage` (the code-owned frontmatter header — Pydantic, additive)

| field | type | set by |
|---|---|---|
| `id` | `str` — `entity:<slug>` / `theme:<slug>` (pattern-validated) | `create_page` |
| `type` | `Literal["entity","theme"]` | `create_page` |
| `title` | `str` | `create_page` |
| `category` | `Optional[str]` (for `index()` grouping) | `create_page` |
| `status` | `Literal["provisional","registered"]` = `"provisional"` | Part 18 discovery lane |
| `state` | `str` (qualitative, e.g. `"slipping"`; `""` until first `record_state`) | brain (4-4); cached here |
| `trajectory` | `str` (e.g. `"on-track -> slipping"`; `""` until first `record_state`) | brain (4-4); cached here |
| `salience` | `float` = `0.0` | **code-computed (4-4)**; cached here |
| `crossRefs` | `list[str]` (page ids) = `[]` | brain (4-4); cached here |
| `createdAsOf` | `str` (YYYY-MM-DD) | `create_page` |
| `lastUpdatedAsOf` | `str` (YYYY-MM-DD) | code-maintained on every mutation |

`body: str` is held alongside the header (not a frontmatter field) — the markdown after the closing fence.
The header splits into two kinds of field:
- **Historized (diff-relevant):** `state` / `trajectory` / `salience` are the **cached current values** of the
  latest `state-change` event in the `log`; the authoritative history is the `log` (§4.1, §5), and `diff`
  reconstructs their as-of values from it.
- **Curated metadata:** `title` / `category` / `status` / `crossRefs` are plain header values — set at
  `create_page` and updated in place via `update_header` (§4). They are **not** historized (they carry no
  temporal series and play no part in `diff`).

The body cites findingIds inline (brain, 4-4); in 4-1 it is an opaque stored string.

**Doctrine note:** `salience` is a number → **computed in code (4-4), never brain-invented** (Part 17). 4-1
only stores it (tests pass it explicitly). `state` / `trajectory` are qualitative judgment labels (like
ratings) — brain-set, allowed.

### 3.2 The frontmatter serializer (no new dependency)

```python
def dump_page(page: WikiPage, body: str) -> str:
    lines = ["---"]
    for key, value in page.model_dump().items():
        lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body

def load_page(text: str) -> tuple[WikiPage, str]:
    if not text.startswith("---\n"): raise WikiFormatError(...)
    _, fm, body = text.split("---\n", 2)             # first two fences only
    header = {}
    for line in fm.splitlines():
        if not line.strip(): continue
        key, _, rest = line.partition(": ")
        header[key] = json.loads(rest)               # bulletproof escaping via stdlib json
    return WikiPage(**header), body
```

- Each value is encoded with `json.dumps` → valid YAML-flow; decoded with `json.loads`. **Round-trip
  correctness depends only on the stdlib `json`** (verified: header/body/types preserved).
- A malformed file (no opening fence, missing closing fence, a non-JSON value) raises `WikiFormatError`
  (fail loud, never a silent half-parse).
- Frontmatter holds only short scalars + one short list (`crossRefs`) → a daily mutation is a small, clean
  diff (the long append-only history is in the `log`, §4.1).

---

## 4. The `WikiStore` interface — `gpu_agent/wiki/store.py`

Backed by a gitignored runtime dir (`store/wiki/`, like `store/`). Holds a `FindingStore` (for resolution) and
a `WikiLog`.

```python
class PageNotFound(KeyError): ...
class DuplicatePage(ValueError): ...

class WikiStore:
    def __init__(self, root, finding_store: FindingStore): ...

    # --- mutate (each auto-appends a LogEvent) ---
    def create_page(self, id, type, title, category=None, *, as_of) -> WikiPage          # raises DuplicatePage
    def append_observation(self, page_id, finding_id, *, as_of) -> WikiPage              # validates finding_id ∈ FindingStore
    def record_state(self, page_id, *, as_of, state, trajectory, salience, finding_id=None) -> WikiPage
    def update_header(self, page_id, *, as_of, **fields) -> WikiPage                      # curated metadata only: title/category/status/crossRefs
    def log_append(self, event: LogEvent) -> None                                        # for brain events (ingest/query/lint) in 4-4

    # --- read ---
    def get_page(self, page_id) -> WikiPage                                              # raises PageNotFound
    def observations(self, page_id) -> list[Observation]                                  # derived from log, ordered (asOf, seq)
    def state_history(self, page_id) -> list[StateChange]                                 # derived from log
    def window(self, page_id, n) -> WindowView                                            # header + body + last-n observations RESOLVED to Findings
    def index(self) -> list[IndexEntry]                                                   # scan page headers; grouped by category
    def diff(self, as_of, prev_as_of) -> WikiDiff
```

- **`append_observation`** refuses an ungated finding: if `finding_id ∉ FindingStore` it **raises** (this is
  the "numbers come only from gated findings" guard). On success it appends an `append-observation` event to
  the log and bumps `lastUpdatedAsOf`.
- **`record_state`** appends a `state-change` event and syncs the page's cached `state/trajectory/salience`.
  Separating it from `append_observation` keeps **facts accreting** (observations) distinct from
  **judgment/computed state** (state changes).
- **`update_header`** updates only curated metadata (`title` / `category` / `status` / `crossRefs`) and bumps
  `lastUpdatedAsOf`. It is **not** a temporal event (no `log` entry), since these fields carry no history and
  don't affect `diff`. The 4-4 brain uses it to set `crossRefs` and to promote `status` provisional →
  registered (the *decision* logic — persist+corroborate — is 4-4; 4-1 provides only the mechanism). Passing
  any field other than the four allowed names raises (fail loud).
- **Auto-logging:** the three **temporal** mutations — `create_page` / `append_observation` / `record_state` —
  each append their own `LogEvent`, so the `log` is a complete provenance trail with no extra caller effort
  (Part 20 replay).

### 4.1 The append-only log — `gpu_agent/wiki/log.py`

`store/wiki/log.jsonl`, one JSON object per line, append-only. **This is the temporal source of truth.**

```python
class LogEvent(BaseModel):
    seq: int                 # monotonic per-store; assigned = (#existing lines); deterministic, no wall-clock
    asOf: str                # logical date YYYY-MM-DD
    kind: Literal["create-page","append-observation","state-change","ingest","query","lint"]
    pageId: Optional[str] = None
    findingId: Optional[str] = None
    state: Optional[str] = None
    trajectory: Optional[str] = None
    salience: Optional[float] = None
    detail: str = ""
```

- **No wall-clock:** `seq` is assigned from the current line count and ordering is `(asOf, seq)` — fully
  deterministic and replayable. `asOf` is always passed in by the caller (tests; the 4-4 daily loop).
- `observations(pageId)` = log events `kind=="append-observation"` for `pageId`, ordered `(asOf, seq)`,
  mapped to `Observation{findingId, asOf}`. `state_history(pageId)` = the `state-change` events similarly →
  `StateChange{asOf, state, trajectory, salience, findingId?}`.
- `log_append` (public) lets the 4-4 brain journal `ingest`/`query`/`lint` events; reading a missing log file
  returns `[]` (cold-start).

### 4.2 `window`, `index` result shapes

- `WindowView = { page: WikiPage, body: str, observations: list[ {asOf, finding: Finding} ] }` — the last-n
  observations **resolved** through `FindingStore`. This is what the 4-5 brief reads (a windowed view, not the
  full history).
- `IndexEntry = { id, type, title, category, status, state, trajectory, salience, lastUpdatedAsOf,
  observationCount, oneLine }` where `oneLine` is composed from `title` + `state` + `trajectory` (no separate
  stored summary). `index()` scans the page headers and returns a **deterministically ordered** list
  (by `category`, then `id`); grouping by category is left to the consumer/display.

---

## 5. `diff(as_of, prev_as_of) -> WikiDiff` — pure function over the log + headers

Because every event is dated, "the store **as of** date D" = the events with `event.asOf <= D`. Let
`existed_at(page, D)` ⇔ the page has any event with `asOf <= D` (its `create-page` event marks birth), and let
the **window** be events with `prev_as_of < event.asOf <= as_of`.

```python
class WikiDiff(BaseModel):
    new_pages:     list[PageDelta]    # existed_at(as_of) and NOT existed_at(prev_as_of)
    changed_pages: list[PageDelta]    # existed_at(prev_as_of) AND ≥1 window event (append/state-change)
    quiet_pages:   list[str]          # existed_at(prev_as_of) AND 0 window events  (feeds 4-4 decay)
    index_moves:   list[IndexMove]    # pages whose state/trajectory/salience changed across the window
```

- `PageDelta = { id, title, newFindingIds: [...], stateTransition: Optional[{from, to}] }` — *what* changed,
  derived from the window events (and, for `stateTransition`, the reconstructed current state at `prev_as_of`
  vs at `as_of`).
- `IndexMove = { id, oldState, newState, oldTrajectory, newTrajectory, oldSalience, newSalience }` —
  reconstructed from the latest `state-change` with `asOf <= prev_as_of` vs `asOf <= as_of`; ranked by
  `|salience delta|` then magnitude. This is the data the 4-5 brief uses to **lead with "what moved today."**
- diff reads the **log** (not the cached header) for as-of correctness; the header cache is only for
  `index()` / display. Fully deterministic → unit-tested with a committed two-day fixture store.

---

## 6. Cold-start, replay, doctrine

- **Cold-start (Part 34):** an empty store → `index() == []`; `get_page` / `window` raise clean `PageNotFound`;
  `observations` / `state_history` on a missing page raise `PageNotFound`; reading a missing `log.jsonl`
  returns `[]`; `diff` over an empty/short history returns empty lists. No crashes on day one.
- **Replay (Part 20):** a page cites findingIds; `FindingStore.get` resolves them deterministically; the
  `log` + the gated findings reconstruct any day. No wall-clock anywhere (`asOf`/`seq` only).
- **Doctrine recap:** code computes + gates + stores; the brain (4-4) curates; **numbers come only from gated
  findings** (`append_observation` enforces; `salience` is code-computed in 4-4); fetched page text is DATA,
  not instructions (the body is an opaque stored string in 4-1); **nothing is silently dropped** — malformed
  files fail loud, id collisions fail loud.

---

## 7. Frozen vs additive (Part 33 / Part 39 self-check)

- **Byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`,
  `gpu_agent/registry/validate.py`, the `Finding` schema, the 6 dimension names, the rating scale,
  `pipeline.py`'s Part-7 gate, the existing `JsonStore`.
- **Additive only:** the new `FindingStore` (in `store.py`), the new `gpu_agent/wiki/` package, and their
  schemas. No existing public signature changes.
- **Reuse, don't rebuild:** `JsonStore` for scorecards (unchanged); the committed-fixture deterministic test
  pattern from A's `report.py` tests; the `Finding` schema as the unit `FindingStore` persists.

---

## 8. Test strategy (deterministic; the A pattern)

All `pytest`, no LLM, no skill. `asOf` always explicit (no wall-clock). Most tests build the store in
`tmp_path` via the public API; a small committed fixture store under `fixtures/wiki/` guards the on-disk
format and the read/diff path.

- `tests/test_finding_store.py` — append/get/exists; idempotent re-append; **id-collision-with-different-
  content raises**; `FindingNotFound`; unsafe-id rejected.
- `tests/test_wiki_page.py` — frontmatter round-trip (header + body + types identical); malformed files raise
  `WikiFormatError`; a body containing `---` survives.
- `tests/test_wiki_store.py` — `create_page` (+ `DuplicatePage`); `append_observation` (+ **ungated-finding
  raises**); `record_state`; `get_page` (+ `PageNotFound`); `window(n)` resolves findings; `index()` catalogs
  + groups; mutating methods **auto-log** the right `LogEvent`s; `seq` is monotonic & wall-clock-free.
- `tests/test_wiki_diff.py` — a two-day fixture store → `diff(day2, day1)` yields the right
  new/changed/quiet/index_moves; cold-start/empty diff is graceful.

The full suite stays green at every commit (baseline **211 passed, 3 skipped**, plus the new tests).

---

## 9. Out of scope (4-4 / later — charter Part 39)

The daily gather sweep; dedup-vs-store; the multi-factor materiality / `lint` engine; the salience-**decay**
computation; the **brain-ingest** seam (`--emit-prompt` + a wiki-ingest skill that routes a finding to its
page, writes the prose body, flags contradictions); promotion `provisional → registered` on persist+
corroborate (Parts 18/10). The two indices (4-3), the leading/daily indicators (4-2), and the market-state
brief (4-5) consume this store but are their own pieces.

---

## 10. Acceptance (4-1)

1. `FindingStore` persists each gated `Finding` once, addressable by id; append is immutable/idempotent and an
   id collision fails loud.
2. A `WikiPage` persists as a markdown file with a no-dependency `key: <json>` frontmatter header + a
   brain-curated body, and round-trips byte-faithfully (header, types, body).
3. `WikiStore` ships the full interface — `create_page`, `append_observation` (refusing an ungated finding),
   `record_state`, `update_header` (curated metadata only), `get_page`, `window(n)` (resolving findings),
   `index()`, `log_append`, and `diff(as_of, prev_as_of)` returning
   `{new_pages, changed_pages, quiet_pages, index_moves}` — all pure code.
4. The append-only `log.jsonl` is the temporal source of truth; `observations` / `state_history` / `window` /
   `diff` derive from it; ordering is deterministic (`asOf`, `seq`) with **no wall-clock**.
5. Cold-start is graceful; every day is replayable from the `log` + gated findings (Part 20).
6. Built **additively**; the **frozen contract is byte-unchanged** (Part 33); the full suite is green.
