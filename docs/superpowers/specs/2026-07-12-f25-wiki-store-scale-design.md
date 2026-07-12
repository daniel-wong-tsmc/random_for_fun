# F25 — Wiki store performance + concurrency (design)

- **Date:** 2026-07-12
- **Status:** Design complete (self-directed / AFK), proceeding to plan → TDD.
- **Provenance:** the user was **not available** during this run. Every design fork is recorded in
  §10 "Decision provenance" and labeled **AFK-precedent — user to confirm at merge review**. Where
  the backlog states a lean, that lean was chosen.
- **Backlog:** this is **F25** (`docs/fix-backlog.md`): "Wiki store performance + concurrency.
  O(N) full-log re-reads per operation, O(pages²) health scans, `seq = len(read())` TOCTOU race —
  fatal at 34 concurrent categories." The larger **canonical-store swap (charter Part 9) is OUT of
  scope** — this makes the *existing* store fast and concurrency-safe with compatible, additive
  changes only.

---

## 1. Problem

The wiki store keeps a single append-only JSONL event log (`store/wiki/log.jsonl`) plus one markdown
file per page. Three defects make it scale badly and become unsafe under concurrency:

1. **O(N) full-log re-read on every operation.** `WikiLog.read()` re-reads and re-parses the entire
   file each call. It is called from nearly every read path: `store._events_for` (→ `observations`,
   `state_history`, and once **per page** inside `index()`), `store.diff`, `lint.quiet_age` (once
   **per page**), `lint._auto_prev`, `lint._contradictions_for`, and `ingest.apply_enrichment`. A
   single `index()` over P pages performs P full-log parses; a single `health_report` performs
   several P× full-log parses.

2. **O(pages²) health scan.** `health_report`:
   - calls `store.index()` (P full-log parses) at the top,
   - loops all pages resolving `observations()` + `quiet_age()` (each a full-log parse) → P×,
   - runs a nested `for pid: for other: if other.title in body` mention scan (P² substring tests)
     where the outer `body` is fetched via `store.window(pid, 0)` — which itself recomputes
     `observations()` (another full-log parse) **per outer page**.
   Net: the genuinely fatal cost is repeated whole-log parsing (≈ P × log_size), stacked on a
   P² substring scan.

3. **`seq = len(self.read())` TOCTOU race.** `WikiLog.append` computes the next sequence number by
   reading the whole log and taking its length, then writes. Two concurrent writers (the "34
   concurrent categories" case) both observe length N and both write `seq = N` → duplicate seq,
   corrupt ordering. It is also an O(N) full re-read per append.

## 2. Goals

- **No full-log re-read per operation** — an in-memory, incrementally-synced cache with correct
  invalidation, plus a per-page index so `_events_for`/`index`/`health` don't rescan the whole log.
- **Health scan no longer O(pages²)** — remove the per-page log parses (via the cache/index) and
  replace the P² substring mention scan with a single-pass multi-substring matcher (Aho-Corasick),
  exact-substring-semantics preserving.
- **Close the seq TOCTOU race** — two concurrent writers can never mint the same seq; proven by a
  multi-process two-writer test.
- **Measured before/after** timings on a synthetic store of a few hundred pages, recorded in §9.
- Stay **deterministic and replayable**; keep **on-disk formats readable by existing code**
  (additive only); **frozen core untouched**; **eval pin green** (no brain-prompt change); suite
  green at every commit; **Windows-safe** locking with no new heavyweight deps.

## 3. Non-goals / out of scope

- The canonical-store swap / storage-engine change (SQLite etc.) — charter Part 9, explicitly out.
- Caching page *markdown files* (the O(pages) per-`index()` page-file reads are linear, not the
  quadratic defect; left as-is to keep scope tight and invalidation simple).
- Any change to emitted brain prompts, the Finding schema, gate/scoring, or `store/` live data.
- Auto-breaking of stale lock files (see §10 fork 7).

## 4. Architecture

Two owned files change plus one new helper module; all under `gpu_agent/wiki/` (owned lane):

- **`gpu_agent/wiki/log.py` (`WikiLog`)** — gains an in-memory cache with a byte-offset cursor, a
  per-page index, an append-time cross-process lock, and a small test-visible instrumentation
  counter. Public API (`read`, `append`, `append_event`) is unchanged in signature and return
  types; two additive read accessors are introduced (`events_for_page`, `count`).
- **`gpu_agent/wiki/store.py` (`WikiStore`)** — `_events_for` and `index` use the new per-page
  accessor instead of filtering a fresh full read; a small `_body(page_id)` helper reads a page's
  body without recomputing observations. No format or signature changes visible to callers.
- **`gpu_agent/wiki/textscan.py` (new)** — a minimal deterministic Aho-Corasick multi-substring
  matcher: build once from all page titles, scan each body once, return the set of matched titles.
  Exact `substring in text` semantics (no word boundaries), cross-checked against a brute-force
  oracle in tests.
- **`gpu_agent/wiki/bench.py` (new)** — a public-API-only benchmark builder that constructs a
  synthetic store of N pages/observations and times append / index / observations / health. Used to
  capture before/after numbers; also imported by the perf test.

### 4.1 WikiLog incremental cache + per-page index

State on the instance:

- `_events: list[LogEvent]` — all parsed events, in file order.
- `_by_page: dict[str, list[LogEvent]]` — page id → its events, in file order.
- `_offset: int` — **byte** offset of the last complete newline-terminated line consumed.
- `parsed_lines: int` — cumulative count of lines parsed from disk (instrumentation only).

`_sync()`: `stat` the file. If size == `_offset`, return (cache fresh — the common case, O(1)). If
size > `_offset`, open `rb`, seek `_offset`, read the delta bytes, split on `b"\n"`, parse only the
**complete** (newline-terminated) lines, extend `_events`/`_by_page`, and advance `_offset` by the
byte length of the consumed complete-line prefix (a trailing partial line — a concurrent mid-write —
is left unconsumed until its newline arrives). If size < `_offset` (truncation/rebuild/`tmp_path`
reuse), reset all state and full-reparse. Splitting on `b"\n"` is safe for UTF-8 bodies because
`0x0A` never occurs inside a multibyte sequence.

`read()` → `_sync(); return self._events`. `events_for_page(pid)` → `_sync(); return
self._by_page.get(pid, [])`. `count()` → `_sync(); return len(self._events)`.

### 4.2 Safe seq minting under a cross-process lock

`append(...)`:

1. Acquire an advisory lock: `os.open(lock_path, O_CREAT|O_EXCL|O_WRONLY)` in a bounded retry loop
   (small sleeps, ~10 s timeout, then raise — fail loud). `lock_path = str(path) + ".lock"`.
2. `_sync()` — pull in any events other writers appended since we last looked.
3. `seq = len(self._events)`.
4. Build the `LogEvent`, append its `json + "\n"` **bytes** to the file (`ab`), `flush`.
5. Update caches in place (`_events`, `_by_page`) and set `_offset` to the new EOF — no reparse of
   our own line.
6. `finally`: close the lock fd, then `os.unlink(lock_path)` (close-before-unlink for Windows).

Because only one writer holds the lock and each re-syncs before step 3, seqs are unique and
contiguous even across processes. Reads take **no** lock (they only ever consume complete lines), so
throughput and determinism are preserved. In single-writer replay/rebuild the behavior is identical
to today (`seq` = number of prior events, 0,1,2,…).

### 4.3 store.py wiring

- `_events_for(page_id, kind)` filters `self.log.events_for_page(page_id)` by `kind`, then sorts by
  `(asOf, seq)` exactly as today (small per-page list).
- `index()`'s per-page `observationCount` uses the same accessor — O(events-for-that-page), not a
  full parse per page.
- `health_report`'s mention scan reads each body once via a direct `_body`/`_read` (no `window`,
  no observations recompute), builds the Aho-Corasick automaton from all non-empty titles once, and
  for each source body emits mention-gaps for the matched target ids — filtered (≠ self, not already
  cross-reffed) and **sorted ascending** to reproduce today's exact append order.

## 5. Data flow / invalidation

Write → append updates the on-disk file and the in-memory caches atomically for that instance;
subsequent reads on the same instance see the new event immediately. Read → `_sync()` re-checks file
size and pulls any externally-appended complete lines. Invalidation signal is **file size vs. byte
offset** — exact for an append-only log, robust to coarse Windows mtime. The lifetime of a cache is
one `WikiStore`/`WikiLog` instance, which matches how the CLI/controller use it (one instance per
command, many ops within).

## 6. Error handling

- Lock acquisition timeout → raise a clear error (fail loud; no silent corruption, no auto-break).
- Partial final line during read → not consumed until complete (no `ValidationError` on half a line).
- File shrank vs. offset → full reparse (handles rebuilds and test `tmp_path` reuse).
- Missing file → empty (unchanged behavior).

## 7. Testing (TDD; every acceptance item pinned)

- **`tests/test_wiki_textscan.py`** — Aho-Corasick: single/multiple/nested (`"AMD"` inside
  `"AMD Instinct"`)/overlapping/absent titles; a randomized property test cross-checking the matcher
  against the naive `title in body` oracle.
- **`tests/test_wiki_log_cache.py`** —
  (1) `read()` twice with no append parses disk lines only once (`parsed_lines` unchanged on the
  second call): **acceptance (1)** no full-log re-read per op;
  (2) a second `WikiLog` on the same file sees the first's appends (external-write sync);
  (3) append restamps monotonic contiguous seq and updates caches without reparse;
  (4) partial trailing line is ignored until its newline arrives.
- **`tests/test_wiki_log_concurrency.py`** — **acceptance (3)**: `ProcessPoolExecutor` with K
  processes each appending M events to one log; assert exactly K×M events and seqs are the full
  contiguous set `0…K×M-1` (no duplicate seq). Module-level worker for Windows spawn.
- **`tests/test_wiki_perf.py`** — **acceptance (1)+(2)** deterministic (non-timing) pins:
  build P pages / E events; assert `health_report` parses the log **at most once**
  (`parsed_lines` delta ≈ E, not P×E); assert `index()` over P pages parses the log at most once.
  Also exposes the timing harness used for §9.
- Existing `tests/test_wiki_*` (log, observations, store, diff, lint_health, v12, …) stay green
  unchanged — they pin the behavior this work must preserve.

## 8. Acceptance mapping

| # | Acceptance | Mechanism | Pinning test |
|---|---|---|---|
| 1 | No full-log re-read per op | incremental byte-cursor cache + per-page index | `test_wiki_log_cache`, `test_wiki_perf` |
| 2 | Health no longer O(pages²) | drop per-page log parses; Aho-Corasick mention scan | `test_wiki_perf`, `test_wiki_textscan` |
| 3 | seq TOCTOU closed | O_EXCL lockfile-guarded read-count+append | `test_wiki_log_concurrency` |
| 4 | Before/after timings recorded | `bench.py` on ~300 pages, numbers in §9 | (recorded below) |

## 9. Before / after measurements

_Synthetic store: 300 pages, 1800 log events (1 create + 5 obs per page), on the shared root venv,
Windows. Measured via `gpu_agent/wiki/bench.py`. Before = pre-optimization (Task 1 commit); After =
final. Times are seconds._

| Operation (P=300, log=1800 events) | Before | After |
|---|---|---|
| build store (1800 appends) | **77.8** | _TBD_ |
| `index()` ×1 | **5.42** | _TBD_ |
| `observations()` ×300 pages | **5.31** | _TBD_ |
| `health_report()` ×1 | **55.8** | _TBD_ |
| log lines parsed during a cold `health_report()` | _TBD_ (≈ P×log) | _TBD_ (≤ log, one pass) |

## 10. Decision provenance

Every pick below is **AFK-precedent — user to confirm at merge review**. Backlog leans chosen where
stated; compatible/additive lean chosen for every on-disk question.

1. **Eliminate O(N) re-reads via an in-instance incremental cache** (vs. an on-disk sidecar index,
   vs. a storage-engine swap). Chosen: in-memory cache + per-page index. Rationale: backlog says
   "index/cache with correct invalidation"; storage swap is out of scope; no on-disk format change.
2. **Invalidation by file size / byte offset** (vs. mtime). Chosen: size/offset — exact for an
   append-only log, robust to coarse Windows mtime.
3. **seq safety via an `O_EXCL` lockfile spinlock** (vs. `msvcrt`/`portalocker`, vs. a seq-counter
   sidecar). Chosen: dependency-free `O_EXCL` lockfile — matches "msvcrt/portalocker-free preferred"
   and "no new heavyweight deps"; Windows- and POSIX-safe.
4. **Reads are lock-free** (vs. shared-lock reads). Chosen: lock-free, complete-line-only — keeps
   throughput and determinism; each op re-syncs at start.
5. **Health mention scan → Aho-Corasick** (vs. leaving a pure-CPU P² substring scan and justifying
   it as "bounded"). Chosen: a genuine sub-quadratic matcher so acceptance (2) is met cleanly, not
   merely argued; exact substring semantics preserved and oracle-tested.
6. **`read()` returns the internal list reference** (vs. a defensive copy each call). Chosen:
   reference — a copy would reintroduce O(N)/call; all existing callers are read-only (verified by
   grep). Documented as read-only.
7. **No auto-breaking of a stale lock** (vs. age-based break). Chosen: fail loud on timeout — safer
   than a break race. **Open for the user:** if a process crashes mid-append the leftover
   `log.jsonl.lock` must be removed manually; revisit if this bites operationally.
8. **Do not cache page markdown files.** Chosen: leave O(pages) page-file reads — they are linear,
   not the quadratic defect; caching them adds invalidation risk for no acceptance benefit.
9. **Benchmark lives in `gpu_agent/wiki/bench.py` + `tests/test_wiki_perf.py`** (vs. `scripts/`,
   which is not in the owned lane). Chosen: owned-lane locations only.

## 11. Risks

- **Behavior drift in health mention scan** — mitigated by an oracle/property test for the matcher
  and by keeping the existing `test_wiki_lint_health.py` pins green.
- **Windows unlink-while-open** — mitigated by close-before-unlink ordering.
- **Lock left behind by a crash** — documented (fork 7); short-held so unlikely; fail-loud rather
  than silent.
- **Eval pin** — no brain prompt touched; `test_evals_baseline_pin.py` must stay green (STOP + report
  if it ever reddens).
