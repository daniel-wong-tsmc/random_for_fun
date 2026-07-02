# Lane D — Gather/Dedup/CLI Robustness (F10, F11, F12, F13-D, F22-D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the data-loss and misattribution paths in the gather/replay plumbing: recorded answers paired to docs with hard-fail on mismatch (F11), L1 dedup that can't permanently swallow changed pages or crash-lost docs (F12), corroboration merge + dispersion instead of recency-collapse (F10), day-grain-safe loud find_prior (F13 report side), and no silent drops in `_pipeline`/`_report` (F22 CLI side).

**Architecture:** `gathering/dedup.py` gets hash-first seen-checks, a filter/record split, and merge/dispersion classification; `llm/recorded.py` gets one-answer-per-call semantics; `cli.py` wires the record-after-write, length hard-fails, and drop logging; `report.py`'s find_prior accepts day-grain names. No frozen file is touched.

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints

- Branch `fix/lane-d`, own worktree, run from its root.
- **You own:** `gpu_agent/gathering/dedup.py`, `gpu_agent/llm/recorded.py`, `gpu_agent/cli.py`, `gpu_agent/report.py` (ONLY `_VERSION_RE` + `find_prior`), and tests: `tests/test_dedup_*.py`, `tests/test_recorded_client.py`, `tests/test_cli_ingest.py`, `tests/test_cli_extract.py`, `tests/test_cli_report.py`, `tests/test_report.py` (find_prior tests only), new `tests/test_lane_d_v12.py`.
- **NEVER edit:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/extraction/*`, `gpu_agent/schema/*`, `gpu_agent/judgment/*`, `gpu_agent/wiki/*`, `gpu_agent/pipeline.py`, `gpu_agent/brief.py`, `report.py` render functions, `fixtures/golden/*`, `fixtures/recorded/*` CONTENT (referencing them by path is fine — another stream regenerates extract-nvda.json in parallel; do not add tests that assert its exact content), `registry/*`, `.claude/skills/*`.
- RecordedClient tests must use a TINY schema defined inside the test (RecordedClient is schema-agnostic) — do NOT embed ExtractionResult-shaped answers in new tests; the extraction draft schema is changing in a parallel stream.
- Tests: `.venv/Scripts/python -m pytest -q`. Full suite green at the end of every task.
- Every commit ends with a `Co-Authored-By:` trailer naming the model doing the work.

---

### Task 1: F11 — recorded answers paired to calls; hard-fail on count mismatch

**Files:**
- Modify: `gpu_agent/llm/recorded.py`, `gpu_agent/cli.py` (`_extract`, `_pipeline`, `_judge`)
- Test: `tests/test_lane_d_v12.py` (new) + update `tests/test_recorded_client.py`

**Interfaces:**
- Produces: `RecordedClient.complete_json` consumes EXACTLY ONE recorded answer per call; internal validation retries re-serve the SAME answer (a deterministically invalid answer fails loud instead of consuming the next doc's answer). New property `RecordedClient.remaining -> int`. CLI: with `--recorded` on extract, `len(answers) != len(docs)` → stderr error + exit 2 (same for pipeline extract stage; judge: `len(answers) != samples` → exit 2).

- [ ] **Step 1: Failing tests** in `tests/test_lane_d_v12.py`:

```python
import json, pytest
from pydantic import BaseModel
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.llm.client import LLMError

class Tiny(BaseModel):
    x: int

def test_invalid_answer_fails_loud_without_consuming_next():
    c = RecordedClient(['{"x": "not-an-int"}', '{"x": 2}'])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", Tiny, "m")       # burns ONLY answer 1
    assert c.remaining == 1
    assert c.complete_json("p", "s", Tiny, "m").x == 2   # answer 2 still paired

def test_one_answer_per_call():
    c = RecordedClient(['{"x": 1}', '{"x": 2}'])
    assert c.complete_json("p", "s", Tiny, "m").x == 1
    assert c.complete_json("p", "s", Tiny, "m").x == 2

def test_exhausted_fails_loud():
    c = RecordedClient([])
    with pytest.raises(LLMError):
        c.complete_json("p", "s", Tiny, "m")
```
CLI mismatch test (subprocess or `main(argv)` style — copy the harness from `tests/test_cli_extract.py`): run `extract --docs fixtures/raw --as-of 2026-06 --recorded <tmp file with 3 answers>` where fixtures/raw has 1 doc → exit 2, stderr contains "recorded answers (3) != documents (1)".

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**

`llm/recorded.py`:
```python
class RecordedClient:
    """Replays canned LLM responses — ONE per complete_json call. A validation failure
    re-serves the same answer to the retry loop, so a bad answer fails loud instead of
    silently consuming the next call's answer (F11: no cross-attribution)."""
    def __init__(self, responses: list[str]):
        self._responses = deque(responses)

    @property
    def remaining(self) -> int:
        return len(self._responses)

    def complete_json(self, prompt, system, schema, model):
        if not self._responses:
            raise LLMError("no recorded response for this call")
        answer = self._responses.popleft()
        return complete_with_retry(lambda *a: answer, prompt, system, schema, model)
```
(Check `complete_with_retry`'s raw-fn signature in `gpu_agent/llm/client.py` first and match it.)

`cli.py` — in `_extract` after loading docs, when `args.recorded`:
```python
        answers = json.loads(pathlib.Path(args.recorded).read_text("utf-8"))
        if len(answers) != len(docs):
            print(f"gpu-agent extract: error: recorded answers ({len(answers)}) != documents ({len(docs)})",
                  file=sys.stderr)
            return 2
        client = RecordedClient(answers)
```
Same guard in `_pipeline` for `--recorded-extract`; in `_judge` for `--recorded` compare against `args.samples`.

- [ ] **Step 4: Full suite** (the emit→recorded round-trip tests still pass: counts already match there).
- [ ] **Step 5: Commit** `fix(F11): recorded replay pairs one answer per call and hard-fails on count mismatch - no silent cross-attribution`

---

### Task 2: F12 — L1 dedup: content-hash first; record only after the snapshot is durable

**Files:**
- Modify: `gpu_agent/gathering/dedup.py` (`SeenDocIndex.contains`, `filter_seen_documents`, new `record_documents`), `gpu_agent/cli.py` (`_ingest`)
- Test: update `tests/test_dedup_seen_docs.py`, `tests/test_cli_ingest.py`; extend `tests/test_lane_d_v12.py`

**Interfaces:**
- Produces: `SeenDocIndex.contains(url_norm, chash)` — a doc is KNOWN only when its CONTENT hash is known (reason "seen-content-hash"; reason "seen-url" when the url is also known — same URL with NEW content is NOT known: stable price pages survive). `filter_seen_documents(docs, index, *, as_of)` no longer records; still drops batch-internal repeats by hash. New `record_documents(docs, index, *, as_of)` records survivors. `_ingest` calls `record_documents` AFTER all doc files + gather-log are written (crash before the write loses nothing forever).

- [ ] **Step 1: Failing tests:**

```python
# 1. same URL, changed content: record(url, hash1); contains(url, hash2) is None  (price page lives)
# 2. same content, new URL: contains(url2, hash1) == ("seen-content-hash", asOf)
# 3. same url+hash: reason "seen-url"
# 4. filter_seen_documents does NOT write to the index file (path unchanged / not created)
# 5. record_documents writes; a second ingest of the same batch drops all docs
# 6. CLI: run ingest with --dedup-store twice on the same blobs; first run ingests N,
#    second drops N; seen_docs.jsonl entries appear only after the first run completed.
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**

```python
    def contains(self, url_norm: str, chash: str):
        """Known iff the CONTENT is known (F12: hash before URL — a stable URL whose
        content changed is a new document, not a seen one)."""
        if chash in self._hash:
            reason = "seen-url" if url_norm in self._url else "seen-content-hash"
            return (reason, self._hash[chash])
        return None

def filter_seen_documents(docs, index, *, as_of):
    """L1 filter — PURE read against the index; recording is the caller's job AFTER the
    snapshots are durably written (F12: crash pre-write must not lose docs forever)."""
    survivors, dropped, batch_hashes = [], [], set()
    for doc in docs:
        url_norm = _normalize_url(doc.url)
        chash = content_hash(doc.content)
        hit = index.contains(url_norm, chash)
        if hit is None and chash in batch_hashes:
            hit = ("seen-content-hash", as_of)
        if hit is not None:
            reason, first_seen = hit
            dropped.append(DroppedDoc(url=doc.url, reason=reason, firstSeenAsOf=first_seen))
            continue
        batch_hashes.add(chash)
        survivors.append(doc)
    return survivors, dropped

def record_documents(docs, index, *, as_of):
    for doc in docs:
        index.record(_normalize_url(doc.url), content_hash(doc.content), as_of)
```
`cli._ingest`: keep the filter where it is; move recording to after BOTH the per-doc writes and the gather-log write:
```python
    (out / "gather-log.json").write_text(json.dumps(log, indent=2), "utf-8")
    if getattr(args, "dedup_store", None):
        record_documents(docs, index, as_of=args.as_of)   # F12: only after snapshots are durable
```
(import `record_documents` alongside the existing dedup imports).

- [ ] **Step 4: Full suite.**
- [ ] **Step 5: Commit** `fix(F12): L1 dedup keys on content, not URL, and records seen only after snapshots are written`

---

### Task 3: F10 — corroboration merge + dispersion instead of recency-collapse

**Files:**
- Modify: `gpu_agent/gathering/dedup.py` (`classify_findings`, `DedupResult`), `gpu_agent/cli.py` (`_wiki_dedup`)
- Test: update `tests/test_dedup_classify.py`, `tests/test_dedup_cli.py`; extend `tests/test_lane_d_v12.py`

**Interfaces:**
- Produces: `DedupResult.outFindings: list[Finding]` (default []) — the NEW+UPDATE representatives to feed wiki-ingest, WITH: (a) evidence of AGREEING batch-mates merged in (corroboration — same (entity, indicator) and `changed(mate, rep)` is False: rep gets the union of evidence entries, deduped by (source, url, date)); (b) `dispersion` set when batch-mates CONFLICT (`changed(mate, rep)` is True): `dispersion="conflicting same-key reports: <detail>; sources: <s1> vs <s2>"` — the conflict is surfaced, not recency-collapsed. Agreeing mates get verdict "duplicate" with detail "corroborates <rep.id>; evidence merged"; conflicting mates keep "superseded by intra-batch latest vintage". `_wiki_dedup` writes `outFindings` (falls back to the old id-filter only if outFindings is empty AND there are keeps — no silent divergence).

- [ ] **Step 1: Failing tests:**

```python
# 1. NVDA D2 $75.2B from doc A (primary) + $75.2B from doc B (secondary), same key:
#    result.outFindings has ONE finding for the key, len(evidence) == 2,
#    the mate is verdict "duplicate" with detail starting "corroborates"
# 2. conflicting values ($75.2B vs $80B) beyond rel_tol:
#    rep.dispersion is not None and mentions both sources; mate detail "superseded..."
# 3. no batch-mates: outFindings == [rep], evidence untouched, dispersion untouched
# 4. CLI wiki-dedup --out-findings: the written JSON contains the merged 2-evidence finding
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** in `classify_findings` (inside the per-key loop, after picking rep/superseded):

```python
        merged = rep
        for s in superseded:
            if not changed(s, rep, config):
                seen = {(e.source, e.url, e.date) for e in merged.evidence}
                extra = [e for e in s.evidence if (e.source, e.url, e.date) not in seen]
                if extra:
                    merged = merged.model_copy(update={"evidence": list(merged.evidence) + extra})
                result.duplicate.append(FindingClass(findingId=s.id, entity=entity, indicatorId=ind,
                                        verdict="duplicate", priorFindingId=rep.id,
                                        detail=f"corroborates {rep.id}; evidence merged"))
            else:
                merged = merged.model_copy(update={"dispersion":
                    f"conflicting same-key reports: {delta_detail(s, merged, config)}; "
                    f"sources: {', '.join(sorted({e.source for e in s.evidence} | {e.source for e in merged.evidence}))}"})
                result.duplicate.append(FindingClass(findingId=s.id, entity=entity, indicatorId=ind,
                                        verdict="duplicate",
                                        detail="superseded by intra-batch latest vintage"))
```
(then classify `merged` vs prior exactly as today; append `merged` to `result.outFindings` when verdict is new/update). Add `outFindings: list[Finding] = Field(default_factory=list)` to `DedupResult`. Update `_wiki_dedup`:
```python
    if args.out_findings:
        deduped = [f.model_dump() for f in result.outFindings]
        pathlib.Path(args.out_findings).write_text(json.dumps(deduped, indent=2), "utf-8")
```

- [ ] **Step 4: Full suite** (update classify tests that asserted the old evidence-count/verdict details; keep their intent).
- [ ] **Step 5: Commit** `fix(F10): corroborating same-key findings merge evidence; conflicts set dispersion instead of recency-collapse`

---

### Task 4: F13 (report side) — find_prior handles day grain and fails loud

**Files:**
- Modify: `gpu_agent/report.py` (`_VERSION_RE`, `find_prior` ONLY), `gpu_agent/cli.py` (`_report`)
- Test: update `tests/test_report.py` find_prior tests; extend `tests/test_lane_d_v12.py`

**Interfaces:**
- Produces: `_VERSION_RE = re.compile(r"^(\d{4}-\d{2}(?:-\d{2})?)-v(\d+)\.json$")` (month OR day grain). `find_prior(..., unmatched: list[str] | None = None)` — additive param; when a `.json` file in the category dir does not match the pattern its name is appended to `unmatched` (never silently skipped). `_report` passes a list and prints one stderr line per unmatched name: `gpu-agent report: note: ignoring non-scorecard file <name>`.

- [ ] **Step 1: Failing tests:**

```python
# 1. store with 2026-06-15-v1.json and 2026-06-20-v1.json (day grain): find_prior for the
#    v20 file returns the v15 path (regex no longer drops them)
# 2. a stray "notes.json" in the dir lands in the unmatched list
# 3. mixed grain sorts lexically: "2026-06" < "2026-06-15" — document this in the test name
#    (grain consistency per category is enforced wiki-side by another stream)
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the regex + the unmatched collection in find_prior's scan loop; wire `_report` to pass `unmatched=[]` and print the notes after the call.
- [ ] **Step 4: Full suite.**
- [ ] **Step 5: Commit** `fix(F13d): find_prior parses day-grain scorecard names and surfaces ignored files`

---

### Task 5: F22 (CLI side) — no silent drops in _pipeline; no silent unreadable prior

**Files:**
- Modify: `gpu_agent/cli.py` (`_pipeline`, `_report`)
- Test: extend `tests/test_lane_d_v12.py`

**Interfaces:**
- Produces: `_pipeline` collects each doc's `outcome.dropped` and prints `DROPPED <id>: <violations>` lines to stderr plus a final `gate dropped N finding(s)` summary — identical style to `_extract`. `_report`'s unreadable-prior branch prints `gpu-agent report: warning: could not load prior <path>: <err>` instead of `pass`.

- [ ] **Step 1: Failing tests:**

```python
# 1. pipeline --recorded-extract with an answer whose draft fails the gate: stderr contains
#    "DROPPED" and "gate dropped 1 finding(s)"; exit code unchanged
#    (craft the recorded answer against the CURRENT FindingDraft schema by round-tripping:
#     build a draft dict from fixtures/recorded/extract-nvda.json's first answer and break
#     one gated field, e.g. set why="" — parse, mutate, re-serialize; do NOT hand-write it)
# 2. report --scorecard <ok> --prior <corrupt file>: stderr contains "could not load prior"
#    (this branch exists) AND the auto-discovery branch: corrupt prior in store -> stderr
#    warning instead of silence
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** in `_pipeline`'s loop:

```python
    findings, dropped = [], []
    for doc in docs:
        outcome = extract_findings(doc, ext_client, as_of=args.as_of, captured_at=captured_at,
                                   extraction_model=args.model, model=args.model)
        findings.extend(outcome.findings)
        dropped.extend(outcome.dropped)
    for d in dropped:
        print(f"DROPPED {d.id}: {'; '.join(d.violations)}", file=sys.stderr)
    if dropped:
        print(f"gate dropped {len(dropped)} finding(s)", file=sys.stderr)
```
In `_report`, replace the bare `except ... pass` with the stderr warning (keep prior=None flow).

- [ ] **Step 4: Full suite.**
- [ ] **Step 5: Commit** `fix(F22d): pipeline and report surface every dropped finding and unreadable prior - nothing silent`

---

## Self-review checklist
- F10/F11/F12/F13-D/F22-D each map to a task; `git diff main --stat` shows only dedup.py, recorded.py, cli.py, report.py (find_prior region), owned tests.
- No new test embeds extraction-draft JSON it hand-wrote (parallel schema change); recorded tests use tiny local schemas or round-trip existing fixtures by path.
- Full suite green.
