# F25 — Wiki store performance + concurrency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing wiki store fast and concurrency-safe — no full-log re-read per op, no O(pages²) health scan, no seq TOCTOU race — with compatible, additive, deterministic changes.

**Architecture:** `WikiLog` gains an in-instance incremental byte-cursor cache + per-page index (kills full-log reparses) and an `O_EXCL` lockfile around seq-mint (closes the race). A new Aho-Corasick matcher (`textscan.py`) replaces the health P² substring scan. A benchmark module (`bench.py`) captures before/after numbers. `WikiStore`/`lint` are rewired to the new accessors.

**Tech Stack:** Python 3, pydantic, pytest. Stdlib only (`os`, `pathlib`, `time`, `collections`, `concurrent.futures`). No new deps.

## Global Constraints

- **Frozen core NEVER edited:** `gate.py`, `scoring.py`, `schema/*`, `judgment/briefing.py`, judge.py aggregation, `pipeline.py`, `sufficiency.py`, the JsonStore. Do not modify `store/` live data.
- **On-disk format under `store/wiki/` stays readable by existing code** — additive/compatible only. The `log.jsonl` line format is unchanged; the only new on-disk artifact is a transient `log.jsonl.lock` created and unlinked within a single `append`.
- **Deterministic replay/rebuild preserved:** single-writer `seq` sequence is identical to today (0,1,2,…).
- **Windows platform:** locking is `os.open(..., O_CREAT|O_EXCL|O_WRONLY)` — no `msvcrt`, no `portalocker`, no new deps.
- **Eval pin green:** no brain-prompt change. If `tests/test_evals_baseline_pin.py` reddens, STOP and report; never touch `fixtures/evals/baseline.json`.
- **Suite green at every commit.** Baseline: 1200 passed, 5 skipped. Run from worktree root: `../../.venv/Scripts/python -m pytest -q`.
- **Commit trailer:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. `git log --oneline -1` before every commit.

---

### Task 1: Benchmark harness + capture BEFORE numbers

**Files:**
- Create: `gpu_agent/wiki/bench.py`
- Test: (none — measurement helper; exercised by Task 6's perf test)

**Interfaces:**
- Produces: `build_synthetic(root, findings_root, *, pages, obs_per_page, as_of="2026-06-01") -> WikiStore`; `time_ops(store, registry, horizons) -> dict[str, float]` returning seconds for `index`, `observations_all`, `health`.

- [ ] **Step 1: Write `gpu_agent/wiki/bench.py`** (public-API only, runs on current code)

```python
"""F25 benchmark helper: build a synthetic wiki store and time the hot ops.
Public-API only so it runs against both the pre- and post-optimization code."""
from __future__ import annotations
import pathlib, time
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid: str) -> Finding:
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06-01",
        indicatorId="gpuSpotPrice", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="e", observedAt="2026-06-01", capturedAt="2026-06-01")


def build_synthetic(root, findings_root, *, pages: int, obs_per_page: int,
                    as_of: str = "2026-06-01") -> WikiStore:
    fs = FindingStore(findings_root)
    store = WikiStore(root, fs)
    for p in range(pages):
        pid = f"entity:e{p:04d}"
        store.create_page(pid, "entity", f"Title{p:04d}", as_of=as_of,
                          body=f"## Title{p:04d}\nbody for page {p}\n")
        for o in range(obs_per_page):
            fid = f"f-{p:04d}-{o:03d}"
            fs.append(_finding(fid))
            store.append_observation(pid, fid, as_of=as_of)
    return store


def time_ops(store, registry, horizons) -> dict:
    ids = [e.id for e in store.index()]
    out = {}
    t = time.perf_counter(); store.index(); out["index"] = time.perf_counter() - t
    t = time.perf_counter()
    for pid in ids:
        store.observations(pid)
    out["observations_all"] = time.perf_counter() - t
    t = time.perf_counter()
    health_report(store, as_of="2026-06-01", contradictions={}, horizons=horizons,
                  config=DEFAULT_LINT_CONFIG)
    out["health"] = time.perf_counter() - t
    return out
```

- [ ] **Step 2: Capture BEFORE numbers** — run against current (unoptimized) code

Run (worktree root):
```bash
../../.venv/Scripts/python -c "import tempfile,pathlib; from gpu_agent.wiki import bench; from gpu_agent.registry.horizon import IndicatorHorizons; from gpu_agent.registry.indicators import IndicatorRegistry; d=pathlib.Path(tempfile.mkdtemp()); s=bench.build_synthetic(d/'wiki', d/'findings', pages=300, obs_per_page=5); hz=IndicatorHorizons.load('registry/indicators.json'); print(bench.time_ops(s, None, hz))"
```
Record the printed dict into spec §9 "Before" column (and the health log-parse count if measurable). Expected: seconds that scale badly (index/health in the many-seconds range for 300 pages).

- [ ] **Step 3: Run the suite** — confirm still 1200 passed / 5 skipped (bench.py adds no test, imports cleanly)

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: `1200 passed, 5 skipped`.

- [ ] **Step 4: Commit**

```bash
git add gpu_agent/wiki/bench.py docs/superpowers/specs/2026-07-12-f25-wiki-store-scale-design.md
git commit -F <heredoc>   # "feat(f25): synthetic wiki bench + before numbers"
```

---

### Task 2: Aho-Corasick multi-substring matcher

**Files:**
- Create: `gpu_agent/wiki/textscan.py`
- Test: `tests/test_wiki_textscan.py`

**Interfaces:**
- Produces: `class MultiSubstringMatcher(patterns: Iterable[str])` with `.matches(text: str) -> set[str]` returning the subset of `patterns` that occur as substrings of `text` (exact `in` semantics, no word boundaries; empty patterns dropped; deterministic).

- [ ] **Step 1: Write the failing tests** — `tests/test_wiki_textscan.py`

```python
import random
from gpu_agent.wiki.textscan import MultiSubstringMatcher


def test_single_match():
    m = MultiSubstringMatcher(["AMD"])
    assert m.matches("Competes with AMD on GPUs") == {"AMD"}


def test_absent():
    m = MultiSubstringMatcher(["AMD", "Intel"])
    assert m.matches("only nvidia here") == set()


def test_nested_substring_both_reported():
    # "AMD" is a substring of "AMD Instinct"; a body with the long one must report BOTH
    m = MultiSubstringMatcher(["AMD", "AMD Instinct"])
    assert m.matches("the AMD Instinct MI300") == {"AMD", "AMD Instinct"}


def test_overlapping_and_multiple():
    m = MultiSubstringMatcher(["aba", "bab"])
    assert m.matches("ababa") == {"aba", "bab"}


def test_empty_patterns_dropped():
    m = MultiSubstringMatcher(["", "x"])
    assert m.matches("xyz") == {"x"}


def test_property_matches_naive_oracle():
    rng = random.Random(1234)
    alpha = "abc"
    for _ in range(300):
        patterns = list({"".join(rng.choice(alpha) for _ in range(rng.randint(1, 4)))
                         for _ in range(rng.randint(1, 6))})
        text = "".join(rng.choice(alpha + " ") for _ in range(rng.randint(0, 30)))
        got = MultiSubstringMatcher(patterns).matches(text)
        want = {p for p in patterns if p and p in text}
        assert got == want, (patterns, text, got, want)
```

- [ ] **Step 2: Run to verify failure**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_textscan.py -q`
Expected: FAIL (`ModuleNotFoundError: gpu_agent.wiki.textscan`).

- [ ] **Step 3: Write `gpu_agent/wiki/textscan.py`**

```python
"""Deterministic Aho-Corasick multi-substring matcher (F25). Exact `pattern in text`
semantics — no word boundaries. Build once, scan each text once: O(sum|pattern| +
|text| + matches) instead of the per-pair O(pages^2 * |body|) substring scan."""
from __future__ import annotations
from collections import deque
from typing import Iterable


class MultiSubstringMatcher:
    def __init__(self, patterns: Iterable[str]):
        # de-dupe, drop empties (an empty pattern would "match" everywhere)
        self._patterns = [p for p in dict.fromkeys(patterns) if p]
        self._goto = [{}]        # node -> {char: node}
        self._fail = [0]
        self._out = [set()]      # node -> set of pattern indices ending here (incl. suffix links)
        self._build()

    def _build(self) -> None:
        for pid, pat in enumerate(self._patterns):
            node = 0
            for ch in pat:
                nxt = self._goto[node].get(ch)
                if nxt is None:
                    nxt = len(self._goto)
                    self._goto.append({})
                    self._fail.append(0)
                    self._out.append(set())
                    self._goto[node][ch] = nxt
                node = nxt
            self._out[node].add(pid)
        q = deque()
        for _, u in self._goto[0].items():
            self._fail[u] = 0
            q.append(u)
        while q:
            r = q.popleft()
            for ch, u in self._goto[r].items():
                q.append(u)
                v = self._fail[r]
                while v and ch not in self._goto[v]:
                    v = self._fail[v]
                self._fail[u] = self._goto[v].get(ch, 0)
                self._out[u] |= self._out[self._fail[u]]

    def matches(self, text: str) -> set:
        found = set()
        node = 0
        for ch in text:
            while node and ch not in self._goto[node]:
                node = self._fail[node]
            node = self._goto[node].get(ch, 0)
            for pid in self._out[node]:
                found.add(self._patterns[pid])
        return found
```

- [ ] **Step 4: Run to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_textscan.py -q`
Expected: PASS (all 6).

- [ ] **Step 5: Commit** — `git add gpu_agent/wiki/textscan.py tests/test_wiki_textscan.py` → "feat(f25): Aho-Corasick multi-substring matcher for health scan"

---

### Task 3: WikiLog incremental cache + per-page index

**Files:**
- Modify: `gpu_agent/wiki/log.py` (`WikiLog.__init__`, `read`; add `_sync`, `_reset`, `events_for_page`, `count`, `parsed_lines`)
- Test: `tests/test_wiki_log_cache.py`

**Interfaces:**
- Produces: `WikiLog.read() -> list[LogEvent]` (unchanged signature, now cached); `WikiLog.events_for_page(page_id: str) -> list[LogEvent]`; `WikiLog.count() -> int`; `WikiLog.parsed_lines: int` (cumulative disk lines parsed — instrumentation).
- Consumes: nothing new. `append` still uses `seq = len(self.read())` in this task (locking added in Task 4).

- [ ] **Step 1: Write the failing tests** — `tests/test_wiki_log_cache.py`

```python
from gpu_agent.wiki.log import WikiLog


def test_second_read_parses_no_new_lines(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    for i in range(5):
        log.append(asOf="2026-06-01", kind="append-observation", pageId="p", findingId=f"f{i}")
    log.parsed_lines = 0            # zero the counter after the writes
    log.read()
    first = log.parsed_lines
    log.read()                      # no append in between
    assert log.parsed_lines == first  # zero additional parses -> cache served it


def test_fresh_instance_reads_once_then_caches(tmp_path):
    w = WikiLog(tmp_path / "log.jsonl")
    for i in range(4):
        w.append(asOf="2026-06-01", kind="append-observation", pageId="p", findingId=f"f{i}")
    r = WikiLog(tmp_path / "log.jsonl")           # cold instance on existing file
    assert r.parsed_lines == 0
    assert len(r.read()) == 4
    assert r.parsed_lines == 4                     # one pass
    r.read()
    assert r.parsed_lines == 4                     # no re-parse


def test_external_append_is_picked_up(tmp_path):
    a = WikiLog(tmp_path / "log.jsonl")
    a.append(asOf="2026-06-01", kind="create-page", pageId="p")
    b = WikiLog(tmp_path / "log.jsonl")
    b.read()
    a.append(asOf="2026-06-02", kind="append-observation", pageId="p", findingId="f1")
    assert [e.kind for e in b.read()] == ["create-page", "append-observation"]


def test_events_for_page_filters(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log.append(asOf="2026-06-01", kind="create-page", pageId="p")
    log.append(asOf="2026-06-01", kind="create-page", pageId="q")
    log.append(asOf="2026-06-02", kind="append-observation", pageId="p", findingId="f1")
    assert [e.kind for e in log.events_for_page("p")] == ["create-page", "append-observation"]
    assert [e.pageId for e in log.events_for_page("q")] == ["q"]


def test_partial_trailing_line_ignored(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text('{"seq":0,"asOf":"2026-06-01","kind":"create-page","pageId":"p"}\n{"seq":1,"asOf"',
                    encoding="utf-8")   # second line has no newline / is truncated
    log = WikiLog(path)
    assert len(log.read()) == 1          # only the complete line is consumed
```

- [ ] **Step 2: Run to verify failure**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_cache.py -q`
Expected: FAIL (`AttributeError: ... 'events_for_page'` / `'parsed_lines'`).

- [ ] **Step 3: Rewrite `WikiLog.__init__` and `read`, add helpers** in `gpu_agent/wiki/log.py`

```python
    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
        self._events: list[LogEvent] = []
        self._by_page: dict[str, list[LogEvent]] = {}
        self._offset = 0                 # byte offset of last complete line consumed
        self.parsed_lines = 0            # instrumentation: cumulative disk lines parsed

    def _reset(self) -> None:
        self._events = []
        self._by_page = {}
        self._offset = 0

    def _sync(self) -> None:
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            if self._offset or self._events:
                self._reset()
            return
        if size == self._offset:
            return
        if size < self._offset:          # truncated / rebuilt / tmp reuse
            self._reset()
        with self.path.open("rb") as fh:
            fh.seek(self._offset)
            chunk = fh.read()
        nl = chunk.rfind(b"\n")
        if nl == -1:
            return                       # only a partial line so far
        complete = chunk[: nl + 1]
        for line in complete.decode("utf-8").split("\n"):
            if not line.strip():
                continue
            ev = LogEvent.model_validate_json(line)
            self._events.append(ev)
            if ev.pageId:
                self._by_page.setdefault(ev.pageId, []).append(ev)
            self.parsed_lines += 1
        self._offset += len(complete)

    def read(self) -> list[LogEvent]:
        self._sync()
        return self._events

    def events_for_page(self, page_id: str) -> list[LogEvent]:
        self._sync()
        return self._by_page.get(page_id, [])

    def count(self) -> int:
        self._sync()
        return len(self._events)
```

(Leave `append` and `append_event` unchanged in this task — `seq = len(self.read())` still works via the cache.)

- [ ] **Step 4: Run cache tests, then the full suite**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_cache.py tests/test_wiki_log.py tests/test_wiki_observations.py tests/test_wiki_store.py tests/test_wiki_diff.py -q`
Expected: PASS.
Then: `../../.venv/Scripts/python -m pytest -q` → `1200 passed + 6 new, 5 skipped` (count grows by new tests).

- [ ] **Step 5: Commit** — "feat(f25): WikiLog incremental byte-cursor cache + per-page index"

---

### Task 4: Close the seq TOCTOU race (lockfile-guarded append)

**Files:**
- Modify: `gpu_agent/wiki/log.py` (`__init__` lock fields; rewrite `append`; add `_acquire_lock`/`_release_lock`)
- Test: `tests/test_wiki_log_concurrency.py`

**Interfaces:**
- Consumes: `_sync`, `_events`, `_by_page`, `_offset` from Task 3.
- Produces: `append(...)` now mints `seq` under an `O_EXCL` lockfile and updates the cache in place (no reparse of its own line). Signature/return unchanged.

- [ ] **Step 1: Write the failing tests** — `tests/test_wiki_log_concurrency.py`

```python
import os, threading
from concurrent.futures import ProcessPoolExecutor
from gpu_agent.wiki.log import WikiLog


def _proc_worker(args):
    path, n, tag = args
    log = WikiLog(path)
    for i in range(n):
        log.append(asOf="2026-07-12", kind="append-observation", pageId="p",
                   findingId=f"f-{tag}-{i}")
    return n


def test_two_writers_processes_no_duplicate_seq(tmp_path):
    path = str(tmp_path / "log.jsonl")
    K, M = 4, 25
    with ProcessPoolExecutor(max_workers=K) as ex:
        list(ex.map(_proc_worker, [(path, M, k) for k in range(K)]))
    seqs = sorted(e.seq for e in WikiLog(path).read())
    assert len(seqs) == K * M
    assert seqs == list(range(K * M))       # unique AND contiguous


def test_many_threads_no_duplicate_seq(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    T, M = 8, 30

    def work(tag):
        for i in range(M):
            log.append(asOf="2026-07-12", kind="append-observation", pageId="p",
                       findingId=f"f-{tag}-{i}")

    threads = [threading.Thread(target=work, args=(t,)) for t in range(T)]
    for th in threads: th.start()
    for th in threads: th.join()
    seqs = sorted(e.seq for e in log.read())
    assert seqs == list(range(T * M))
```

- [ ] **Step 2: Run to verify failure**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_concurrency.py -q`
Expected: FAIL — duplicate/non-contiguous seq under the current `seq = len(self.read())` (race), especially the process test.

- [ ] **Step 3: Add lock fields + rewrite `append`** in `gpu_agent/wiki/log.py`

Add imports at top: `import os`, `import time`. Add to `__init__`:
```python
        self._lock_path = str(self.path) + ".lock"
        self._lock_timeout = 10.0
```
Add helpers and rewrite `append`:
```python
    def _acquire_lock(self) -> int:
        deadline = time.monotonic() + self._lock_timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                return os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"wiki log lock busy: {self._lock_path}")
                time.sleep(0.005)

    def _release_lock(self, fd: int) -> None:
        os.close(fd)                      # close BEFORE unlink (Windows)
        try:
            os.unlink(self._lock_path)
        except FileNotFoundError:
            pass

    def append(self, *, asOf, kind, pageId=None, findingId=None, state=None,
               trajectory=None, salience=None, detail="") -> LogEvent:
        fd = self._acquire_lock()
        try:
            self._sync()                              # absorb any external appends first
            seq = len(self._events)                   # race-free: we hold the lock
            event = LogEvent(seq=seq, asOf=asOf, kind=kind, pageId=pageId,
                             findingId=findingId, state=state, trajectory=trajectory,
                             salience=salience, detail=detail)
            data = (event.model_dump_json() + "\n").encode("utf-8")
            with self.path.open("ab") as fh:
                fh.write(data)
                fh.flush()
                self._offset = fh.tell()              # advance cursor past our own line
            self._events.append(event)                # update cache in place (no reparse)
            if event.pageId:
                self._by_page.setdefault(event.pageId, []).append(event)
            return event
        finally:
            self._release_lock(fd)
```

- [ ] **Step 4: Run concurrency tests, then full suite**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_concurrency.py tests/test_wiki_log.py -q`
Expected: PASS.
Then full suite → green.

- [ ] **Step 5: Commit** — "feat(f25): lockfile-guarded seq mint closes wiki log TOCTOU race"

---

### Task 5: Rewire store + lint to the fast accessors; Aho-Corasick health scan

**Files:**
- Modify: `gpu_agent/wiki/store.py` (`_events_for`; add `_body`)
- Modify: `gpu_agent/wiki/lint.py` (`quiet_age`; `health_report` mention scan)
- Test: existing `tests/test_wiki_lint_health.py` (must stay green — behavior pin)

**Interfaces:**
- Consumes: `WikiLog.events_for_page` (Task 3); `MultiSubstringMatcher` (Task 2).
- Produces: `WikiStore._body(page_id: str) -> str`.

- [ ] **Step 1: Rewrite `WikiStore._events_for` and add `_body`** in `gpu_agent/wiki/store.py`

```python
    def _events_for(self, page_id, kind) -> list[LogEvent]:
        evs = [e for e in self.log.events_for_page(page_id) if e.kind == kind]
        return sorted(evs, key=lambda e: (e.asOf, e.seq))

    def _body(self, page_id: str) -> str:
        """The page's markdown body (no observation resolution). Raises PageNotFound."""
        return self._read(page_id)[1]
```

- [ ] **Step 2: Rewrite `lint.quiet_age`** to use the per-page accessor (semantics identical)

```python
    materials = [e.asOf for e in store.log.events_for_page(page_id)
                 if e.kind in ("append-observation", "state-change")
                 and e.asOf <= as_of]
```

- [ ] **Step 3: Rewrite the `health_report` mention scan** in `gpu_agent/wiki/lint.py`

Add import near the top: `from gpu_agent.wiki.textscan import MultiSubstringMatcher`.
Replace the mention-without-link block (the second `for pid, p in sorted(pages.items())` loop) with:
```python
    title_to_ids: dict[str, list[str]] = {}
    for other_id, other in pages.items():
        if other.title:
            title_to_ids.setdefault(other.title, []).append(other_id)
    for ids in title_to_ids.values():
        ids.sort()
    matcher = MultiSubstringMatcher(title_to_ids.keys())
    for pid, p in sorted(pages.items()):
        present = matcher.matches(store._body(pid))
        targets = [oid for title in present for oid in title_to_ids[title]
                   if oid != pid and oid not in p.crossRefs]
        for other_id in sorted(targets):
            gaps.append(CrossRefGap(source=pid, target=other_id, reason="mention-without-link"))
```
(The asymmetric-crossref loop above it is unchanged; mention gaps still append after the asymmetric ones, in source-then-sorted-target order — byte-identical to before.)

- [ ] **Step 4: Run the health + lint + movement + lifecycle tests**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_lint_health.py tests/test_wiki_lint_materiality.py tests/test_wiki_lint_decay.py tests/test_brief_movement.py tests/test_lifecycle_promotion.py tests/test_lifecycle_prune_quarantine.py -q`
Expected: PASS (behavior preserved).
Then full suite → green.

- [ ] **Step 5: Commit** — "perf(f25): store/lint use per-page log index; Aho-Corasick health scan"

---

### Task 6: Perf pins (parse-count) + AFTER numbers

**Files:**
- Create: `tests/test_wiki_perf.py`
- Modify: `docs/superpowers/specs/2026-07-12-f25-wiki-store-scale-design.md` (§9 table AFTER column + parse counts)

**Interfaces:**
- Consumes: `bench.build_synthetic` (Task 1); `WikiLog.parsed_lines`, `count` (Task 3).

- [ ] **Step 1: Write the perf pins** — `tests/test_wiki_perf.py`

```python
from gpu_agent.wiki import bench
from gpu_agent.wiki.store import WikiStore
from gpu_agent.store import FindingStore
from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG
from gpu_agent.registry.horizon import IndicatorHorizons

_HZ = IndicatorHorizons.load("registry/indicators.json")


def test_warm_index_and_health_do_not_reparse_log(tmp_path):
    bench.build_synthetic(tmp_path / "wiki", tmp_path / "findings", pages=40, obs_per_page=4)
    store = WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))  # cold instance
    total = store.log.count()               # one warm-up pass
    base = store.log.parsed_lines
    assert base == total                    # exactly one pass to warm the cache
    store.index(); store.index()
    health_report(store, as_of="2026-06-01", contradictions={}, horizons=_HZ,
                  config=DEFAULT_LINT_CONFIG)
    assert store.log.parsed_lines == base   # ZERO additional parses -> no full-log re-read per op


def test_cold_health_parses_log_at_most_once(tmp_path):
    bench.build_synthetic(tmp_path / "wiki", tmp_path / "findings", pages=40, obs_per_page=4)
    store = WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))  # cold
    assert store.log.parsed_lines == 0
    health_report(store, as_of="2026-06-01", contradictions={}, horizons=_HZ,
                  config=DEFAULT_LINT_CONFIG)
    # a single full pass, NOT O(pages) passes: parsed lines <= total event count
    assert store.log.parsed_lines <= store.log.count()
```

- [ ] **Step 2: Run the perf pins**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_perf.py -q`
Expected: PASS.

- [ ] **Step 3: Capture AFTER numbers** — same one-liner as Task 1 Step 2, plus the health parse count

Run the Task 1 Step 2 one-liner again (post-optimization). Also capture the cold-health parse count:
```bash
../../.venv/Scripts/python -c "import tempfile,pathlib; from gpu_agent.wiki import bench; from gpu_agent.wiki.store import WikiStore; from gpu_agent.store import FindingStore; from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG; from gpu_agent.registry.horizon import IndicatorHorizons; d=pathlib.Path(tempfile.mkdtemp()); bench.build_synthetic(d/'wiki', d/'findings', pages=300, obs_per_page=5); s=WikiStore(d/'wiki', FindingStore(d/'findings')); hz=IndicatorHorizons.load('registry/indicators.json'); print('ops', bench.time_ops(s, None, hz)); s2=WikiStore(d/'wiki', FindingStore(d/'findings')); health_report(s2, as_of='2026-06-01', contradictions={}, horizons=hz, config=DEFAULT_LINT_CONFIG); print('health_parsed', s2.log.parsed_lines, 'of', s2.log.count())"
```
Fill spec §9 AFTER column with the new seconds and the parse counts (before ≈ P×E, after ≈ E once).

- [ ] **Step 4: Full suite + eval pin explicit check**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: `120X passed, 5 skipped` (baseline 1200 + new tests). Confirm `tests/test_evals_baseline_pin.py` is among the passing.

- [ ] **Step 5: Commit** — "test(f25): parse-count perf pins + record before/after numbers"

---

## Self-Review

- **Spec coverage:** §4.1 cache → Task 3; §4.2 lock → Task 4; §4.3 store/health wiring → Task 5; textscan → Task 2; bench/§9 numbers → Tasks 1+6; acceptance table §8 → Tasks 3/4/5/6 tests. All covered.
- **Placeholder scan:** none — every code step shows full code; §9 numbers are captured by an exact command.
- **Type consistency:** `events_for_page`, `count`, `parsed_lines`, `_body`, `MultiSubstringMatcher.matches`, `build_synthetic`, `time_ops` used consistently across tasks.
- **Ordering:** bench+before (1) → textscan (2) → cache (3) → lock (4) → wiring (5) → pins+after (6). Each ends green.
