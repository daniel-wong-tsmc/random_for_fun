# F78 Stage 4 — Fresh-gather rework: 7-day sweep + logged discretionary pursuit (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the standard/live gather "Recency window" — today `recencyDays = 45` + a **hard-drop** of any non-filing lead older than the window — with (a) a **7-day initial sweep** (round-1 seeds carry last-7-days qualifiers), (b) a **discretionary-pursuit** rule (the agent MAY chase an older-than-7-day lead when the content is materially worth it; no auto-drop), and (c) a new `pursuedDespiteAge[]` log entry (age + one-line justification) for each kept document older than the sweep — symmetric to `skipped[]`, so discretion is auditable, never silent (charter Part 29). Filing-URL seeds stay exempt. Fold the now-redundant "Daily mode" vs "standard mode" recency distinction into the single 7-day sweep (spec §5.1 cadence collapse), scoped to the recency/pursuit/logging block only.

**Architecture:** This is **mostly coordinator skill prose** in `.claude/skills/gather-category/SKILL.md` (the standard "Recency window (live mode)" block and the Daily-mode "Recency window" step) plus **one small, real code change**: `pursuedDespiteAge[]` rides the same `blobs.json` snapshot-envelope → `gpu_agent/cli.py::_ingest` → `gather-log.json` plumbing that `skipped[]` already rides, so it lands in the replayable snapshot and earns a real pytest. `gather-log.json` has **no pydantic model** (it is a plain dict built in `_ingest`, cli.py lines ~99-111; `skipped` flows from `payload.get("skipped", [])`, line ~86, into `log["skipped"]`, line ~106) — so the field is pinned by (a) a `_ingest` carry-through pytest and (b) skill-prose grep/proofread pins. The gather-category skill is **coordinator prose, not an emitted brain prompt**, so changing it does not trip the eval pin.

**Tech Stack:** Markdown skill prose; Python 3.11, argparse (`gpu_agent.cli`), pytest. Run Python as `.venv/Scripts/python` from repo root (from the worktree: `../../.venv/Scripts/python`).

**Spec:** `docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md` §5.4 (this is D6 in §4; reworks F58, supersedes F58's window rule per §10) and §5.1 (cadence collapse — "Daily mode" and "standard mode" merge). Live evidence in §1: v4's gather logged **0 recency drops** yet pulled in a **320-day** NVIDIA product/spec page (2025-08-22) with no recency record — old pages entered silently. This is **F78 Stage 4** of the build order (§9 step 3); it is independent of Stages 1–3.

## Global Constraints

- **Determinism / doctrine:** caps, skips, and now discretionary-pursuits are **LOGGED, never silent** (charter Part 29). No wall-clock: the coordinator writes document dates it already has; no new `Date.now()`.
- **Frozen core untouched:** do NOT modify `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`. The gather-category skill is **COORDINATOR prose, NOT an emitted brain prompt** — changing it does NOT trip the eval pin. This stage touches only `.claude/skills/gather-category/SKILL.md`, `gpu_agent/cli.py` (`_ingest` only), and `tests/test_cli_ingest.py` (additive case).
- **Eval pin stays green:** `tests/test_evals_baseline_pin.py` must stay green — this stage changes **no** extraction/judgment/thesis prompt file. If it goes red, you touched a prompt file — stop and re-scope.
- **Gather-log field pin:** if a `pursuedDespiteAge[]` field were added to a gather-log **pydantic model**, add a real pytest for it. There is **no** such model (plain JSON dict in `_ingest`), so the field is pinned via (a) the `_ingest` carry-through pytest (Task 3) AND (b) the skill-prose grep/proofread pins (Tasks 1, 2, 4).
- **Execution happens in a git worktree** per repo discipline: branch `fix/f78-stage4-fresh-gather` in its own `.worktrees/f78-stage4-fresh-gather`, run from its root; one shared root venv (never a per-worktree venv). `git log --oneline -1` immediately before every commit (concurrent-instance guard). Feature work never happens on the root checkout's main.
- **Suite green at every commit.** Baseline before starting: run `.venv/Scripts/python -m pytest -q` and record the pass/skip count.
- **Windows:** use the Bash tool for `>` redirects / heredocs; **no double quotes** inside `git commit -m` under PowerShell (write the message via a bash heredoc). Commit trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Standard "Recency window (live mode)" → 7-day sweep + discretionary pursuit

**Files:** `.claude/skills/gather-category/SKILL.md` — the **"Recency window (live mode)"** block inside "Round building: manifest-seeded" (currently lines ~135-144). Skill prose only; no code.

**Why:** Today the standard path drops any non-filing lead older than a 45-day window (`recencyDays = 45`). D6 replaces this with a 7-day initial sweep and lets the agent *keep* an older lead by judgment — the v4 root cause was that this window was advisory prose with no auditable record when an old page was kept anyway.

- [ ] **Step 1: Read the exact current block.** In `.claude/skills/gather-category/SKILL.md`, the block currently reads (verbatim, ~lines 135-144):

```
**Recency window (live mode).** Bias the round-1 search-query seeds (free-web query seeds,
standard slices, headline slices, forward-signal slices) and the on-topic lead filter (step 4)
to the last **N days** (a dial; default `recencyDays = 45` — wider than Daily mode's
`recencyDays = 7`, since this is the periodic full-crawl path, not a daily "what's new" sweep).
Add "since <date> / past month / latest" style qualifiers to those queries, scaled to the
45-day window. Unlike those query-built seeds, filing-URL seeds are exempt: the priority seeds
bullet's `urlPatterns` matches are attempted as-is, with no date qualifier and no drop, because
a fresh 10-K or 10-Q legitimately cites and discusses older reporting periods. DROP any
non-filing lead whose document date is older than the window (log it in `skipped[]` as
`"lead '<x>' older than recency window (<date>)"`), exactly like Daily mode step 1.
```

- [ ] **Step 2: Replace the whole block** with the 7-day-sweep + discretionary-pursuit prose below (Edit tool; match the exact old text above as `old_string`):

```
**Recency window (live mode) — 7-day initial sweep.** Bias the round-1 search-query seeds
(free-web query seeds, standard slices, headline slices, forward-signal slices) and the on-topic
lead filter (step 4) to the last **N days** (a dial; default `recencyDays = 7`). Add
"since <date> / past week / latest" style qualifiers to those queries, scaled to the 7-day
window. This 7-day net is the **initial sweep**, not a hard boundary — it decides what the
round-1 seeds *reach for*, not what may ultimately be kept.

Filing-URL seeds are exempt from the sweep: the priority seeds bullet's `urlPatterns` matches
are attempted as-is, with no date qualifier and no age check, because a fresh 10-K or 10-Q
legitimately cites and discusses older reporting periods. Filing seeds never need a
`pursuedDespiteAge` entry.

**Discretionary pursuit (documents older than the 7-day sweep).** A non-filing lead whose
document date is older than the 7-day window is **no longer auto-dropped**. The agent MAY chase
and keep it when it judges the content materially worth it (e.g. a still-authoritative
spec/pricing page, or a structural announcement with no fresher restatement). Discretion is not
free: when you KEEP such a document, you MUST record it — never silent (Part 29). Log each kept
older-than-sweep document in `pursuedDespiteAge[]` (written to the snapshot envelope, step 5)
with its age and a one-line justification:
`{"ref": "<url-or-lead>", "date": "<doc date>", "ageDays": <n>, "reason": "<one line: why this stale doc earns its place>"}`.
This is **symmetric to `skipped[]`**: `skipped[]` records what a cap or window turned *away*;
`pursuedDespiteAge[]` records what the sweep would have turned away but the agent chose to
*keep*. An older document you do NOT keep needs no entry — it simply was not gathered. This
closes the v4 gap where a 320-day page entered the corpus with zero recency record.
```

- [ ] **Step 3 (pin — grep):** run from the worktree root:

```bash
grep -nE "7-day initial sweep|recencyDays = 7|Discretionary pursuit|pursuedDespiteAge\[\]|symmetric to .skipped" .claude/skills/gather-category/SKILL.md
```

Expected: the standard-block hits are present, and the phrase `recencyDays = 45` no longer appears **in the standard block** (Task 4 removes the last remaining `= 45` cross-reference if any survives). Confirm with:

```bash
grep -n "recencyDays = 45\|45-day window\|hard-drop\|DROP any\b" .claude/skills/gather-category/SKILL.md
```

Expected: **zero hits** after Tasks 1 and 4 both land (the standard block no longer hard-drops). If Task 4 has not run yet, the only surviving `DROP any` hit is Daily-mode step 1 (line ~260) — remove it in Task 4.

- [ ] **Step 4: Proofread** that the block still sits inside "Round building: manifest-seeded" (before "2b. Discovery-role leads"), that the filing-exempt sentence is intact, and that the JSON entry shape matches what Task 2/Task 3 use.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/gather-category/SKILL.md
git commit -m "$(cat <<'EOF'
docs(F78-4): standard gather recency becomes a 7-day sweep + discretionary older-lead pursuit (reworks F58)

Replaces recencyDays=45 hard-drop with a 7-day initial sweep; older non-filing
leads may be kept by judgment and are logged in pursuedDespiteAge[] (Part 29).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Log discretionary pursuits in the snapshot envelope + invariant + report

**Files:** `.claude/skills/gather-category/SKILL.md` — the **Invariants** block (~lines 16-19), the **"Write the snapshot envelope"** step 5 (~lines 221-222), the **Report** step 8 (~lines 243-249), and **Snapshot determinism** (~line 315). Skill prose only; no code.

**Why:** For discretion to be auditable, `pursuedDespiteAge[]` must be a first-class, replayable log field alongside `skipped[]`/`coverageGaps`/`webReach`, declared in the invariants and reported at run end.

- [ ] **Step 1: Add a symmetric invariant.** After the existing "Caps are logged, never silent" bullet (currently: `- **Caps are logged, never silent.** When a cap stops the run, record what you skipped in \`skipped[]\`.`), insert:

```
- **Discretionary pursuits are logged, never silent.** When you keep a non-filing document older
  than the 7-day recency sweep, record it in `pursuedDespiteAge[]` (age + one-line reason), the
  keep-side twin of `skipped[]` (Part 29). Filing-URL seeds are sweep-exempt and need no entry.
```

- [ ] **Step 2: Add the field to the snapshot envelope.** Change step 5 (currently):

```
**5. Write the snapshot envelope** to `blobs.json`:
`{"rounds": <n>, "skipped": [<notes>], "blobs": [<all unique blobs>]}`.
```

to:

```
**5. Write the snapshot envelope** to `blobs.json`:
`{"rounds": <n>, "skipped": [<notes>], "pursuedDespiteAge": [<older-than-sweep keeps>], "blobs": [<all unique blobs>]}`.
`pursuedDespiteAge` is carried through by `ingest` into `gather-log.json` exactly as `skipped` is
(each entry `{"ref","date","ageDays","reason"}`); an empty list is the norm when every kept
document is inside the 7-day sweep.
```

- [ ] **Step 3: Report the count at run end.** In step 8 ("**8. Report:**"), the counts bullet currently reads:

```
- documents gathered (primary vs secondary, duplicates, dropped, skipped)
```

Change it to:

```
- documents gathered (primary vs secondary, duplicates, dropped, skipped, pursuedDespiteAge)
```

and add a bullet after the "Coverage gaps" bullet:

```
- **Pursued despite age: K** — documents kept older than the 7-day sweep; if K > 0, list each
  as `<ref> (<ageDays>d): <reason>` so the reader sees exactly which stale docs the run chose to keep.
```

- [ ] **Step 4: Extend Snapshot determinism.** The line currently reads:

```
`docs/` + `gather-log.json` (including `coverageGaps` and the `webReach` health block) + `blobs.json` are the saved artifacts.
```

Change the parenthetical to:

```
`docs/` + `gather-log.json` (including `coverageGaps`, `pursuedDespiteAge`, and the `webReach` health block) + `blobs.json` are the saved artifacts.
```

- [ ] **Step 5 (pin — grep):**

```bash
grep -nE "Discretionary pursuits are logged|pursuedDespiteAge|Pursued despite age" .claude/skills/gather-category/SKILL.md
```

Expected: the invariant, the step-5 envelope, the step-8 report bullets, and the Snapshot-determinism line all appear (≥ 5 hits). Proofread the envelope JSON key ordering is legal JSON and the entry shape matches Task 1 and Task 3.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/gather-category/SKILL.md
git commit -m "$(cat <<'EOF'
docs(F78-4): pursuedDespiteAge[] is a first-class gather-log field (invariant, envelope, report, determinism)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Thread `pursuedDespiteAge` through `_ingest` into `gather-log.json` (+ real pytest)

**Files:**
- Modify: `gpu_agent/cli.py` (`_ingest` only — the `payload.get(...)` reads and the `log` dict; ~lines 82-107)
- Modify: `tests/test_cli_ingest.py` (extend `test_ingest_writes_docs_and_log`; add default-empty assertion)

**Why:** `skipped[]` already rides `blobs.json` → `_ingest` → `gather-log.json` (`payload.get("skipped", [])` → `log["skipped"]`). Threading `pursuedDespiteAge` the same way makes it (a) genuinely symmetric to `skipped`, (b) part of the deterministic replayable snapshot, and (c) pinned by a real automated test rather than prose alone. `gather-log.json` has no pydantic model, so this dict carry-through is the correct, minimal seam. `cli.py` is **not** frozen core; `_ingest` touches no prompt bytes, so the eval pin stays green.

**Interfaces:**
- Consumes: `payload["pursuedDespiteAge"]` (optional; default `[]`) from the blobs snapshot envelope.
- Produces: `gather-log.json` gains a top-level `pursuedDespiteAge` list, carried through verbatim (the coordinator owns each entry's `{ref,date,ageDays,reason}` shape — `_ingest` does not validate it, exactly as it does not validate `skipped[]` strings).

- [ ] **Step 1: Write the failing test.** In `tests/test_cli_ingest.py`, extend `test_ingest_writes_docs_and_log` (the envelope at ~line 11) to include the new key, and assert it round-trips into the log:

```python
    blobs.write_text(json.dumps({
        "rounds": 2,
        "skipped": ["lead 'amd-rumor' dropped by maxDocuments cap"],
        "pursuedDespiteAge": [
            {"ref": "https://nvidia.example/h100-spec", "date": "2025-08-22",
             "ageDays": 320, "reason": "still-current H100 spec page; no fresher restatement"},
        ],
        "blobs": [_blob("https://www.sec.gov/nvda/10q"),
                  _blob("https://www.sec.gov/nvda/10q/#dup"),   # duplicate
                  _blob("https://some-blog.example/post"),
                  {"url": "https://x.example/bad", "entity": "nvidia",
                   "source": "S", "date": "2026-05"}],          # malformed (no content)
    }), "utf-8")
```

and after the existing `log["skipped"] == [...]` assertion (~line 36) add:

```python
    assert log["pursuedDespiteAge"] == [
        {"ref": "https://nvidia.example/h100-spec", "date": "2025-08-22",
         "ageDays": 320, "reason": "still-current H100 spec page; no fresher restatement"},
    ]
```

Also extend the bare-array default test (`test_ingest_accepts_bare_array`, ~line 46) so the default is pinned:

```python
    assert log["rounds"] == 0 and log["documents"] == 1 and log["skipped"] == []
    assert log["pursuedDespiteAge"] == []
```

- [ ] **Step 2: Run it — verify it fails.**

Run: `.venv/Scripts/python -m pytest tests/test_cli_ingest.py -k "writes_docs_and_log or bare_array" -q`
Expected: FAIL with `KeyError: 'pursuedDespiteAge'` (the log dict has no such key yet).

- [ ] **Step 3: Implement the carry-through in `gpu_agent/cli.py::_ingest`.** In the object branch (currently):

```python
    else:
        blobs = payload.get("blobs", [])
        rounds = payload.get("rounds", 0)
        skipped = payload.get("skipped", [])
```

add one line:

```python
        pursued_despite_age = payload.get("pursuedDespiteAge", [])
```

and in the bare-array branch (currently `blobs, rounds, skipped = payload, 0, []`) add the default:

```python
        blobs, rounds, skipped, pursued_despite_age = payload, 0, [], []
```

Then in the `log = { ... }` dict, after `"skipped": skipped,`, add:

```python
        "pursuedDespiteAge": pursued_despite_age,
```

(Note: this key sits in the always-written log body, next to `skipped` — NOT inside the `if args.dedup_store` block, so a non-dedup standard run still carries it.)

- [ ] **Step 4: Run it — verify it passes.**

Run: `.venv/Scripts/python -m pytest tests/test_cli_ingest.py -q`
Expected: PASS (all ingest tests, including the extended two).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cli.py tests/test_cli_ingest.py
git commit -m "$(cat <<'EOF'
feat(F78-4): ingest carries pursuedDespiteAge[] from the blobs envelope into gather-log.json (symmetric to skipped)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Fold "Daily mode" recency into the single 7-day sweep (recency block only)

**Files:** `.claude/skills/gather-category/SKILL.md` — the **Daily-mode "1. Recency window"** step (~lines 258-261). Skill prose only; **scoped strictly to the recency block** — do NOT touch Daily mode's caps (step 4), cadence prioritization (step 2), numeric-scrape sweep (step 3), or dedup wiring (step 5). Do NOT rebuild the whole cadence (that is spec §5.1's job, folded into F78 Stages 1/5).

**Why:** With the standard path now at `recencyDays = 7`, the Daily-mode-vs-standard recency distinction is redundant (spec §5.1: "Daily mode" and "standard mode" merge; the differences become dials/caps, not two recency procedures). Daily mode step 1 also still hard-drops older leads — which now contradicts the standard block's discretionary-pursuit rule. Unify them.

- [ ] **Step 1: Replace the Daily-mode recency step.** Currently (verbatim, ~lines 258-261):

```
**1. Recency window.** Bias every seed search and the on-topic filter to the last **N days** (a dial;
default `recencyDays = 7`). Add "since <date> / past week / latest" style qualifiers to the round-1 queries and
DROP any lead whose document date is older than the window (log it in `skipped[]` as
`"lead '<x>' older than recency window (<date>)"`). This is a "what's new" sweep, not a full re-crawl.
```

Replace with:

```
**1. Recency window (the shared 7-day sweep).** Recency behavior is now **identical to the
standard path** — see the standard "Round building" block's "Recency window (live mode) — 7-day
initial sweep" and "Discretionary pursuit" rules. Bias every seed search and the on-topic filter
to the last 7 days (`recencyDays = 7`) with "since <date> / past week / latest" qualifiers; a
non-filing lead older than the sweep is **not hard-dropped** but may be pursued by judgment and,
when kept, logged in `pursuedDespiteAge[]` (filing-URL seeds sweep-exempt). Daily mode no longer
owns a separate recency rule; it differs from the standard path only in its **caps** (step 4)
and **dedup wiring** (step 5). This is still a "what's new" sweep, not a full re-crawl.
```

- [ ] **Step 2 (pin — grep):**

```bash
grep -n "DROP any\b\|recencyDays = 45\|older than recency window" .claude/skills/gather-category/SKILL.md
```

Expected: **zero hits** — the hard-drop language is gone from both the standard block (Task 1) and Daily mode (this task). Then:

```bash
grep -nE "shared 7-day sweep|not hard-dropped" .claude/skills/gather-category/SKILL.md
```

Expected: the Daily-mode unification hit is present.

- [ ] **Step 3: Proofread** that Daily mode steps 2-5 (cadence prioritization, numeric-scrape sweep, caps, dedup wiring) are **unchanged** — only step 1's recency prose moved. Confirm nothing in this task altered caps or dedup:

```bash
grep -n "maxRounds = 2\|maxDocuments = 10\|wiki-dedup\|droppedKnown" .claude/skills/gather-category/SKILL.md
```

Expected: those Daily-mode lines still present and untouched.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/gather-category/SKILL.md
git commit -m "$(cat <<'EOF'
docs(F78-4): fold Daily-mode recency into the shared 7-day sweep; remove the redundant hard-drop (spec 5.1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Full-suite reconciliation, eval-pin check, and the deferred live-verification

**Files:** none edited unless a suite failure surfaces (none expected — this stage adds an optional log key and changes only prose).

- [ ] **Step 1: Run the full suite.**

Run: `.venv/Scripts/python -m pytest -q`
Expected: green at the recorded baseline (expect 3-4 skips). The only new/changed tests are the two `tests/test_cli_ingest.py` cases from Task 3. If any other test references the ingest log shape, reconcile it deterministically (the new `pursuedDespiteAge` key is additive; existing assertions on `skipped`/`documents`/etc. are unaffected).

- [ ] **Step 2: Confirm the eval pin is green (evidence, not assumption).**

Run: `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`
Expected: PASS. This stage changed no emitted extraction/judgment/thesis prompt bytes — only coordinator skill prose and `cli.py::_ingest` (a plumbing dict). If it goes red, you touched a prompt file — stop and re-scope.

- [ ] **Step 3: Confirm the frozen core is untouched.**

Run: `git diff --name-only main...HEAD`
Expected: exactly `.claude/skills/gather-category/SKILL.md`, `gpu_agent/cli.py`, `tests/test_cli_ingest.py`, and this plan doc. NO hit for `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`, or any `extraction/*`/`extraction/prompt.py`.

- [ ] **Step 4: Named deferred live-verification (NOT run in this stage — record it in the handoff).**

> **Deferred live-verification — F78-4 fresh-gather rework.** A subsequent **live** cycle's `work/**/gather-log.json` must show: (1) round-1 seed queries carry **7-day** ("past week / since <date>") qualifiers, not the old 45-day/past-month wording; (2) a **populated `pursuedDespiteAge[]`** whenever a non-filing document older than 7 days is kept — each entry with `ageDays` + a one-line `reason` — OR an explicit empty list `[]` with no stale non-filing doc in the corpus; and (3) **no** silent old page (the v4 failure: a 320-day page in the corpus with zero recency record). Cross-check: every gathered secondary doc with `date` older than `asOf − 7d` has a matching `pursuedDespiteAge` entry (filings exempt). This is the D6 acceptance signal; it cannot be proven from unit tests (it needs a real web crawl), so it is deferred to the next live run and named in `docs/superpowers/HANDOFF.md`.

- [ ] **Step 5: Finish the branch** per repo discipline (superpowers:finishing-a-development-branch): update `docs/superpowers/HANDOFF.md` with the deferred live-verification above, write the `.superpowers/handoffs/<lane>-DONE.md` sentinel, and leave the branch ready for merge review. Do NOT merge under an AFK-default.

---

## Self-review

- **Spec coverage (§5.4 / D6):** (a) 7-day initial sweep → Task 1 (`recencyDays = 7`, round-1 qualifiers scaled to 7 days); (b) discretionary-pursuit rule (no auto-drop) → Task 1 ("no longer auto-dropped", agent MAY keep by judgment); (c) `pursuedDespiteAge[]` log of each kept older-than-sweep doc (age + one-line justification), symmetric to `skipped[]` → Tasks 1-3 (prose + invariant + envelope + `_ingest` carry-through); filing-URL seeds exempt → Tasks 1, 2, 4; §5.1 cadence collapse (one recency rule) → Task 4. Scope held to recency/pursuit/logging — caps, cadence prioritization, numeric-scrape, and dedup wiring are explicitly untouched (Task 4 Step 3 pins this).
- **Gather-log has NO pydantic model** — it is a plain dict built in `cli.py::_ingest` (skipped rides `payload.get("skipped", [])` → `log["skipped"]`). So the field is pinned by BOTH a real pytest (Task 3, the `_ingest` carry-through, mirroring the existing `skipped` assertion) AND skill-prose grep pins (Tasks 1, 2, 4). The one pydantic model in the neighborhood, `manifest.CoverageGap`, governs `coverageGaps` only and is not touched.
- **Symmetry with `skipped[]`:** literal — same snapshot envelope (`blobs.json` step 5), same `_ingest` plumbing, same "in the log, never silent" doctrine. `skipped[]` = window/cap turned away; `pursuedDespiteAge[]` = window would have turned away but agent kept.
- **Frozen core / eval pin:** only `SKILL.md` (coordinator prose, not an emitted brain prompt), `cli.py::_ingest` (no prompt bytes), and a test — Task 5 Steps 2-3 verify the eval pin green and the frozen core untouched by `git diff --name-only`.
- **Determinism:** no wall-clock added; the coordinator writes document dates it already holds. The field lands in the replayable `gather-log.json` snapshot.
- **Placeholders:** none — every prose edit quotes the exact current lines and gives the exact replacement; every code step shows the real diff; every pin is an exact `grep`/`pytest` command.
- **Not in this stage (correctly deferred):** rendering `pursuedDespiteAge` in the brief (renderer / D7 = Stage 5), recalibrating the 7-day threshold (spec §3: ship the mechanism, tune later), and the corpus-side aging that also gates stale content (Stage 3).
