# Artifact landing map — full reference

Verified against `main @ 1a9eb33`, 2026-07-06. Re-verify with the commands at the bottom of
`SKILL.md` before trusting any specific count here — this is a snapshot, not a contract.

## .gitignore, verbatim (the literal definition of "canonical")

```
.venv/
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
.superpowers/
# store/: the CANONICAL run history (scorecards, wiki, dedup index, cycle log) is TRACKED (F1);
# only scratch/demo subtrees stay ignored.
store/*
!store/chips.merchant-gpu/
!store/cycle-log.json
!store/wiki/
!store/findings/
!store/seen_docs.jsonl
!store/theses/
work/
blobs.json
.worktrees/
```

Anything under `store/` not matched by a `!` negation stays ignored — including legacy scratch
subtrees observed live: `store/_brain`, `store/_demo`, `store/_demo_docs`, `store/_docs`,
`store/_dryrun_docs`, `store/live`, `store/live_run`, `store/live_sc`. These mirror real run-dir
shapes (their own nested `docs/`, `blobs.json`, even a nested `store/`) from early bring-up —
never read prior state from them.

A **new** category directory (e.g. `store/models.frontier-closed/`) needs its own
`!store/<id>/` line added before its first live run, or its scorecards land in an ignored
directory and silently never get committed. As of 2026-07-06 no such carve-out exists and
`store/models.frontier-closed/` does not exist on disk — confirming that category has never run
live end-to-end, despite being config-runnable (F27).

`blobs.json` is ignored **by name anywhere in the repo** — a path like
`store/<x>/blobs.json` would still silently not be tracked.

## The cycle-log's two shapes

**Bare plan** (`CyclePlan` in `gpu_agent/cycle.py`) — written by `cycle-plan --out
work/<run-dir>/cycle-plan.json` at Step 1, never at `store/cycle-log.json` directly (F74 guard):

```json
{
  "scope": "category:chips.merchant-gpu",
  "entries": [
    {"category_id": "chips.merchant-gpu", "assignment_path": "fixtures/asg.chips.merchant-gpu.json", "status": "ready"}
  ],
  "stages": [
    {"tier": "category", "status": "active"},
    {"tier": "layer", "status": "deferred"},
    {"tier": "main", "status": "deferred"}
  ]
}
```

An entry's only legal bare keys are `category_id` / `assignment_path` / `status` — this is
exactly the set `tests/test_store_cycle_log_integrity.py` and `cli._is_bare_plan` check against.

**Finalized journal** (session-authored at Step 6, written to `store/cycle-log.json`) — real
example, field names verified against the committed 2026-07-05 daily entry:

```
{scope, asOf, mode, capturedAt,           # all four required; asOf/mode/capturedAt didn't
                                            # exist on the bare plan — their presence IS the
                                            # "this is a real journal" signal
 entries: [{
   category_id, assignment_path, status,
   scorecard,                              # path to store/<id>/<asOf>-v<n>.json
   dmi, smi, sdgi,                         # the three headline numbers, for quick scanning
   gather: {mode, recencyDays, caps, rounds, docsIngested, primaryVsSecondary,
            blobsByClass, webReach, webReachNote, discoveryLeads, blobs, gatherLog,
            coverageGaps, coverageGapCounts, notableSkips, paywalledSkipped},
   dedup: {L1: {ingested, dup, dropped, droppedKnown, note},
           L2: {new, update, duplicate, report}},
   answers: {extract, judge, thesis},      # work/ paths to the saved subagent answers
   gates: {extract, voiceLint, sufficiency, thesis, knownGap},   # free-text outcome per gate
   wikiWriteBack: "<free text: N deduped findings routed, lint summary>",
   stageStatus: {category, thesis, layer, main},   # done|failed|skipped / deferred
   thesis: {judgmentsApplied, deferred, notable, proposed},
   report: "<free text: one-line summary of the rendered report>",
   corpus: null                            # present only when the F62 corpus merge ran
 }],
 stages: [{tier, status}, ...]}
```

`gates.sufficiency` and `gates.voiceLint` are exactly where a bypass gets logged — e.g. the
2026-07 flagship v3's committed journal (git history at `99ca522`) carries
`gates.sufficiency: "bypassed - moat Weak->Mixed forced by +0.50 anchor..."`. **This is the only
place a bypass is recorded** — the rendered report's `TRUST & COVERAGE` section says nothing
about it (F75 open finding).

## `store/chips.merchant-gpu/` directory shape (2026-07-06 snapshot)

```
2026-06-v1.json .. 2026-06-v12.json        # 12 same-month reruns from early bring-up
2026-07-02-v1.json                          # day-grain daily scorecard
2026-07-03-v1.json                          # day-grain daily scorecard
2026-07-05-v1.json                          # day-grain daily scorecard (d9cfb3f)
2026-07-v1.json / -v2.json / -v3.json       # month-grain monthly flagship (v3 = current, 99ca522)
dedup-2026-07-02.json / -03.json / -05.json # L2 DedupReport per daily run
```

`2026-07` sorts lexically *before* `2026-07-02` — the monthly flagship is not the max-sorting
filename in its own directory. `find_prior`/version-resolution logic in `report.py` is
grain-aware; don't hand-roll a "highest filename wins" heuristic.

`store/findings/` held 52 files at last count (one immutable JSON per gated finding id).
`store/theses/chips.merchant-gpu/` holds `book.json` + `history.jsonl` (do not hand-edit
`book.json` — it is rebuilt from `history.jsonl` and load fails loud on drift).
`store/wiki/entity/` held 5 pages at last count: `amd.md`, `nvda.md`, `nvidia.md`, `market.md`,
`multi.md` — note `nvda`/`nvidia` are two separate pages for one company (open item F24, entity
canonicalization; not this skill's fix).

## `work/` directory naming (observed, not a spec — resolve a run's own paths from its cycle-log
entry, not by guessing the directory name)

Styles seen on this machine: `<category>-<asOf>` (`chips.merchant-gpu-2026-07`), bare `<asOf>`
(`2026-07`), `daily-<date>` (`daily-2026-07-03`, `-05`, `-06`), `gather-<date>`, `eval-<date>`,
plus older ad hoc names (`merchant-gpu-2026-06`, `chips.merchant-gpu-run2`/`run3`). A same-day
`daily-<today>` directory containing only `cycle-plan.json` + discovery leads (no answers, no
findings) is the signature of a run that was started and not finished — check for one before
starting a duplicate.
