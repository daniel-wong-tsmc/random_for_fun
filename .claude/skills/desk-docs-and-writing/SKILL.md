---
name: desk-docs-and-writing
description: Use when reading or writing any doc of record in this repo (docs/fix-backlog.md, docs/superpowers/HANDOFF.md, docs/agent-swarm-charter.md, docs/migrations/*, eval run-notes) and two sources disagree about status; a fix-backlog checkbox looks stale or contradicts git; drafting a new F-item entry, migration doc, eval run-notes file, or HANDOFF top section; unsure which doc outranks another; writing outward-facing brief/report prose for a non-technical executive reader; readme.md or START-HERE.md numbers look wrong; choosing a commit message scope prefix.
---

# Desk Docs and Writing

## Overview

This repo has many documents and exactly one truth order. A doc of record is not "the truth" by
virtue of being written down — it is a claim with a maintenance contract, and the contract (not
your judgment about what "should" be true) tells you how to reconcile it against git. The single
most expensive mistake an incoming engineer or model makes here is trusting a checkbox, a stale
count, or a founding doc's math over what git and the running code actually show.

## When to use / When NOT to use

Use this skill to find out **which doc to believe**, **what shape a new doc entry must have**, and
**how outward-facing prose must read**. Do NOT use it for:

| You need... | Go to |
|---|---|
| How a change gets classified/gated, wave/lane mechanics, Part-33 migration procedure, F-item lifecycle rules | `desk-change-control` |
| Diagnosing *why* something failed right now | `desk-debugging-playbook` |
| The chronicle of past investigations/dead ends | `desk-failure-archaeology` |
| Design rationale, invariants, seams | `desk-architecture-contract` |
| What a Finding/rating/index/dimension *means* | `market-state-reference` |
| A specific CLI flag or env var | `desk-config-and-flags` |
| Eval replicate math, hash-pin mechanics, fixture families | `desk-validation-and-qa` |
| Mechanically writing/updating `HANDOFF.md` this session | the user-level `desk-handoff` skill (this skill defines the *shape* it must produce, not the procedure) |
| Orienting at session start | the user-level `resume-desk` skill |
| What you're allowed to *claim* externally about this project | `desk-external-positioning` (this skill owns *how* to write; that one owns *what* you may say) |

## 1. The trust order — memorize this before reading anything else

```
registry/*.json + gpu_agent/ code
        >  docs/migrations/*.md
        >  docs/superpowers/HANDOFF.md  (TOP SECTION ONLY)
        >  docs/agent-swarm-charter.md
        >  founding docs (category-agent-guide.md, ai-market-state-map.md)
        >  readme.md / START-HERE.md / sp4-relaunch-prompt.md   (fossils — verify, don't quote)
```

Why this order: code and registry data are what actually ran; migrations are the only sanctioned
record of frozen-core change; HANDOFF's top section is the newest human-written status; the
charter is the governing doctrine but amended slower than reality; the founding docs are
pre-implementation design concepts that code has since superseded in specific, checkable ways;
the bottom tier is written once and then abandoned.

**Known supersessions — do not cite the founding docs for these, ever:**

| Founding-doc claim | Superseded by (verified 2026-07-06) |
|---|---|
| `category-agent-guide.md` treats price (`D6`) as a scored demand indicator with a weight | `registry/indicators.json`: `"D6": {"dimension": null, "side": "price", "weight": 0.0, "scoring": false}` — price is a display overlay only (contract v1.2, F8) |
| The guide standardizes every indicator to a **z-score** before indexing | `gpu_agent/bands.py` — z-scores were removed (contract v1.2, F36: `"z=" → "a="`, the `zscore` helper deleted); the only sanctioned magnitude vocabulary today is `bands.py`'s five words (§4 below) |
| The guide's `D1…X5` metric-registry slots imply ~31 indicators | `registry/indicators.json` has **17** indicators today (10 scoring), one entry per id, re-verify: `.venv/Scripts/python -c "import json; print(len(json.load(open('registry/indicators.json'))['indicators']))"` |
| Confidence as a number/percentage anywhere in the founding docs or your own drafting instinct | `gpu_agent/schema/finding.py:28` — `level: Literal["low", "medium", "high"]`. Confidence is always one of three words, never a number |

**readme.md is stale — verified 2026-07-06 (HEAD `1a9eb33`):** it says "suite 417 passed / 3
skipped", "F1–F49", "six 2026-06 scorecards", and "`models.frontier-closed` ... not yet runnable
end-to-end." Actual, this session: **1066 passed / 4 skipped** (`.venv/Scripts/python -m pytest -q`);
backlog runs through **F76**; `models.frontier-closed` is *runnable-per-pins* (an assignment,
manifest, and passing scoring proof exist) but **has never produced a live scorecard** — no
`store/models.frontier-closed/` directory exists, and that directory is not even in the
`.gitignore` store whitelist yet. Use that exact phrase — "runnable-per-pins, never yet run live" —
rather than either the README's "not runnable" or the backlog's bare "DONE."

**`docs/superpowers/START-HERE.md` is a fossil, not a half-truth — verify before trusting any
"DONE" backlog note that claims to have touched it.** It still opens with "⬜ Next: write the
code" and describes a dead `CLAUDE_CODE_OAUTH_TOKEN` backend. Backlog item F44 claims "DONE
7b93be3: ... START-HERE.md describes the dead OAuth backend" (fixed) — but `git log --oneline -1
-- docs/superpowers/START-HERE.md` shows its only touch is the file's original creation commit
(`4816a42`); commit `7b93be3` never modified it. **Lesson: a backlog item marked DONE that names a
doc does not prove that doc was actually edited — check the file's own git log, not just the
checkbox.** `docs/superpowers/sp4-relaunch-prompt.md` is the same class of fossil (a relaunch
prompt for a sub-project phase long since merged) — treat any doc whose own last commit predates
the feature it claims to describe as suspect until you check.

**The cautionary tale that got fixed — the "amend one sentence, orphan another" gap.** For most of the
library's life `docs/agent-swarm-charter.md` Part 37 said two contradictory things: line ~1575 ("Hard
multi-source corroboration landed as **F63 (contract v1.3)**: three distinct publishers ... unlock one
bounded step ...") while the Part's closing deferred-list sentence, ~60 lines later, still read "Not yet
(deferred, by decision): hard corroboration...". The F63 amendment updated its own paragraph but never
revisited the closing sentence. **Reconciled 2026-07-06** (maintainer ruling: state the shipped reality):
the deferred-list sentence now says the *staged* 3-publisher step **shipped** as F63/F2e and narrows
"deferred" to the **full Part 26 hard-corroboration requirement + a hard secondary-confidence cap** that
genuinely remain unbuilt. The lesson survives the fix: an amendment inside a Part does not revisit the
Part's other sentences — you must. Re-verify the reconciliation held: `grep -n "staged multi-source
corroboration\|Still deferred (by decision)" docs/agent-swarm-charter.md`.

## 2. Docs of record and their maintenance contracts

### `docs/fix-backlog.md` — the defect/feature ledger

**Entry anatomy** (one bullet per F-item): bold `F<n> — <one-line symptom>`, then evidence with a
file:line citation, then the fix shape, then an italic wave/lane tag (`*(Lane A)*`, `*(Wave 0 —
DONE <hash>)*`) or a note that it is feature-track (brainstorm→spec→plan→SDD, not a lane — that
execution grammar belongs to `desk-change-control`, not repeated here). A closed item appends
**STATUS**, merge hash(es), and suite count at merge time. Worked example (real, verified against
git — F74, merged and checked as of `1a9eb33`):

> `- [x] **F74 — post-run writer clobbers the session-authored cycle log. DONE (merged to main
> 257cf1b, 2026-07-05, user go; suite on merged main 1066/4).** Born 2026-07-05: ... Fix: (1)
> immediate — identify the writer ...; (2) the writer must merge/append, never overwrite ...; (3)
> guard test ...; (4) rule: the session-authored log is canonical; machine writers extend it.
> Acceptance: clobber scenario test-pinned; restored log recommitted; the offending writer named in
> the fix commit. **STATUS 2026-07-05: implemented on branch `f74-cycle-log`.** Writer identified:
> `cli._cycle_plan` blind `write_text` ...`

Note the shape: symptom, code citation, numbered fix plan, and acceptance criteria were all
written into the entry's original ("Fix: (1)...(4)... Acceptance: ...") text *before* the fix
existed — that is what let the later "STATUS ... implemented" paragraph be checked against the
entry's own pre-stated criteria instead of graded after the fact.

**Checkbox-staleness caveat (re-verified 2026-07-06, HEAD `1a9eb33`):** these items are **merged to
main** but their checkbox still reads `- [ ]`: **F56 (core), F57, F58, F59, F61, F63, F68.** F62,
F69, F70, F74 are correctly ticked `- [x]`. Never trust a checkbox alone:

```bash
git log --oneline --grep="F63"                  # find the closing/merge commit
git merge-base --is-ancestor 017b592 HEAD; echo $?   # 0 = it is an ancestor of HEAD (merged)
```

Lookup order when content and checkbox disagree: **HANDOFF top section → `git log --grep=F<n>` →
the backlog entry's prose** (rich and accurate on *what* was done, just not on the box). The
lifecycle rules that govern F-item minting, sequencing, and closure are owned by
`desk-change-control` §6 — this skill only owns the entry's document shape and the reconciliation
habit above.

### `docs/agent-swarm-charter.md` — amendment style

Amendments land **inside** the Part they amend, as a sentence or clause citing the F-item that
authorized them (e.g., "landed as **F63 (contract v1.3)**" inside Part 37, not a new Part 40). They
do not get their own changelog section. This is *load-bearing* prose, not incidental — but see §1
above: amending one sentence inside a Part does not guarantee every other sentence in that Part
gets revisited. **When you land a charter amendment, grep the rest of the Part for stale "not yet"
/ "deferred" language your change may now contradict, and reconcile it in the same edit rather than
leaving a silent gap** — the Part 37 deferred-list contradiction (unreconciled for weeks, fixed
2026-07-06; see §1) is the cautionary tale, not a template to repeat.

### `docs/migrations/` — the two precedents define the required shape

Every frozen-core change (`gate.py`, `scoring.py`, the `Finding` schema, the six dimensions, the
rating scale) ships as **one versioned migration doc**, never a bare commit. Two exist; a third
must follow their shape:

| | v1.2 (`2026-07-contract-v1.2.md`) | v1.3 (`2026-07-contract-v1.3.md`) |
|---|---|---|
| Date / approval | 2026-07-02, user-approved | 2026-07-04, user-approved (cites the F63 design spec) |
| Rule changes | 14, one line each by F-id | exactly 1 (F2e: ≥3 distinct publishers unlocks high confidence) |
| `schemaVersion` | bumped 1.1 → **1.2** | **unchanged** — stays 1.2 (no schema *field* changed) |
| Sections | Rule changes · The D6 flip · schemaVersion bump · shadow-run/replay · "would old data pass the new gate?" | Rule change · **Deliberately unchanged** (what did NOT move, stated explicitly) · Companion doctrine (non-frozen changes riding the same branch) |

Lesson from the pair: a migration does not have to touch the schema version to count as one — v1.3
proves a single-rule, schema-unchanged migration is still a first-class migration doc as long as
it touches the frozen surface. The **shadow-run + replay** procedure (recompute old data under new
math without re-gating history) and golden-fixture regeneration are mechanics owned by
`desk-validation-and-qa` / `desk-proof-and-analysis-toolkit` — cite them, do not re-derive them
here.

### `docs/superpowers/HANDOFF.md` — the resume-point doctrine

**Only the top section (title line + first bullet block) is the resume point.** Everything below
accretes as `## HISTORICAL — ...` blocks or dated coordination notes and is *deliberately*
superseded-but-kept for archaeology — an incoming session that acts on a lower section instead of
the top one will redo or mis-order work that is already done. Teach this exact rule: **trust the
title block, verify below.**

Real top section as of 2026-07-06 (HEAD `1a9eb33`) — quoted to show the shape, not to be trusted
by the time you read this; re-run the re-verification command in §Provenance to get the current one:

> `# HANDOFF — GPU Category Agent (resume point: daily #1 of 2 DONE gate-clean; daily #2 runs
> tomorrow; blind ablation awaits USER scoring)`
> - Date, one-line state-of-the-world, the store commit hash the state rests on, what gate passed
>   with no bypass this time, voice-lint/re-dispatch counts, thesis promotion counts, a named
>   **known gap** logged rather than hidden, eval-pin status, and an explicit **NEXT:** line.

The `## ⚠ CONCURRENT-INSTANCE COORDINATION (still live)` section is a living roster of in-flight
and DONE lanes (branch names, worktree paths, merge hashes, sentinel filenames) — read it before
touching any `.worktrees/` entry. The mechanical procedure for *updating* HANDOFF (verify pushed,
gather live state, prepend, label AFK-defaults, commit+push) is owned by the user-level
`desk-handoff` skill; this skill owns the shape the output must have.

### Eval run-notes commits — the `docs(eval)` pattern

The single most transferable pattern in this repo: **a losing attempt, committed as first-class
documentation, with its disposition written down before the result existed.** Real excerpt
(`docs/superpowers/eval-notes/2026-07-04-f63-run-notes.md`, committed alongside `345fc31`):

> **Pre-committed disposition (recorded BEFORE any record-grade)**
> PASS -> `gpu-agent eval rebaseline --out ... --reason "..."` , commit baseline + RUN-NOTES, full
> suite green.
> One FAIL -> diagnose per-case vs baseline, run ONE full replication.
> Two FAILs -> STOP, keep the pin red, record BLOCKED-on-user with both runs' data.
> **NOT retry-until-green.**
>
> ... [two full runs later] ...
>
> Both runs failed -> per the pre-committed disposition the run STOPS here: pin stays red, no
> rebaseline, no `--force`, NOT retry-until-green.

The disposition table was written *before* either run existed, and the run-notes file records both
the FAIL and *why* it was diagnosed as bar-noise rather than a regression — that diagnosis, not a
hand-wave, is what let the next session (eval-v2) fix the actual problem instead of re-fighting the
same fight blind. The replicate math, verdict ladder, and hash-pin mechanics behind this are owned
by `desk-validation-and-qa`; this skill owns the write-up shape.

## 3. Templates (derived from the real instances above)

Compact skeletons below; fill-in-the-blank versions with inline commentary are in
`references/templates.md`.

**New F-item entry:**
```
- [ ] **F<n> — <one-line symptom, present tense>.** <2-4 sentences: where it lives (file:line or
  behavior), why it matters (must-have vs should-have reasoning), the fix shape as numbered steps
  if non-trivial. Acceptance: <a checkable condition, not "looks better">. *(<Lane letter> | Wave N
  | feature-track: brainstorm→spec→plan→SDD)*
```

**Migration doc skeleton** (`docs/migrations/<date>-contract-v<N>.md`):
```
# Contract v<N> migration — <date>

The <ordinal> sanctioned frozen-core migration (charter Part 33; user-approved <date> in <link to
design spec if one exists>). <One sentence: does it bump schemaVersion or not, and why.>

## Rule change(s)
- **F<id>** — <one line: old behavior -> new behavior, cite the enforcing file/function>.

## Deliberately unchanged
- <name the adjacent things a reviewer might assume also changed, and say they didn't>.

## Companion doctrine (same branch, not frozen-core)
- <non-frozen code/doctrine that rides with this migration, if any>.
```

**Eval run-notes skeleton** (`docs/superpowers/eval-notes/<date>-<label>-run-notes.md`):
```
# Eval run <date> (<F-id>) — <one line: what triggered the re-gate>

Trigger: <which SYSTEM prompt(s) changed, which commit>.
Procedure: .claude/skills/run-eval/SKILL.md; run root: work/<dir>/ (worktree/branch if any).
Incumbents: extract <x> / judge <y> / thesis <z> (source: current baseline).

## Pre-committed disposition (recorded BEFORE any record-grade)
PASS -> <rebaseline command + suite check>.
One marginal-fail -> <replication rule>.
Hard-fail (or two fails) -> STOP, <what stays red, what does NOT happen>. NOT retry-until-green.

## Gate + grade-wave setup
<record-brain attempts, F38 re-dispatches by case id, transport-normalization notes>

## Verdict
<seam scores vs bars, per-case breakdown>

## Diagnosis
<for every point lost: does it trace to the prompt change, or is it coverage/grader variance?
Quote the evidence, not a guess.>

## Disposition executed
<what actually happened, per the pre-committed table>

## Fix-backlog candidates surfaced by this run
<each one becomes its own future eval-gated change, not folded in silently>
```

**HANDOFF top-section skeleton:**
```
# HANDOFF — GPU Category Agent (resume point: <one line, present-tense state>)

- **Date:** <date> (<session marker: morning/evening, what just happened>)
- **Repo:** <url>
- <State-of-the-world bullet(s): what ran, on what commit, which gate passed/failed and how,
  any bypass used (name it — never bury it), counts (re-dispatches, promotions, new proposals)>
- <Known gap(s) logged, not hidden — name the F-item if one exists>
- <Any item still OPEN that blocks the next milestone — name it and why>
- **NEXT:** <the single next action, unambiguous>

## HISTORICAL — <prior state> (superseded by the section above)
<prior top sections demoted here verbatim or summarized — never deleted>

## ⚠ CONCURRENT-INSTANCE COORDINATION (still live)
<roster: F-item/lane -> branch, worktree, sentinel file, merge hash, status>
```

## 4. House style for outward text (briefs, reports, board-facing prose)

The reader is **a real TSMC executive, not an "executive-grade" quality bar**
(`docs/action-items.md:54`) — write as if a specific skeptical, time-poor person will read this
once and act on it.

- **No AI/doctrine/internal jargon in rendered output.** Words like "Finding", "gate",
  "corroboration doctrine", "the brain", "sufficiency check", "anchor bound" are this repo's
  internal vocabulary — they must never leak into a rendered brief. If you are drafting
  outward-facing prose (a brief, a report, an ablation write-up), run it through the `stop-slop`
  skill if it is available in your environment.
- **Magnitude words are closed vocabularies, not stylistic choices.** DMI/SMI-style momentum
  values render as one of `bands.py`'s five words only — **accelerating / firm / flat / softening /
  contracting** — never a synonym, never the raw number (raw indices are trust-footer-only,
  charter Part 17). Dimension ratings render as one of `rating-anchors.md`'s five words —
  **Very strong / Strong / Mixed / Weak / Very weak** — bounded by the anchor, decided within the
  band by the discriminators in that doc (owned by `market-state-reference`; this skill only owns
  the rule "these words only, never invented ones").
- **Confidence is a word, not a percentage** — see §1.
- Every number in outward prose must trace to a cited Finding; never restate a raw index as if it
  were self-explanatory to a reader with no context on what "0.067" means.

## 5. Commit-message conventions (observed; verified against `git log`, 2026-07-06)

| Prefix | Meaning | Real example |
|---|---|---|
| `feat(<scope>):` | New capability/mechanism | `feat(F63): re-gate PASS under eval-v2 - rebaseline to F63 bundle` |
| `fix(<scope>):` | Bug/defect fix | `fix(F74): cycle-plan must never destroy the finalized cycle journal` |
| `docs(<scope>):` | Doc-of-record change (backlog, handoff, spec, plan, migration, eval-notes) | `docs(handoff): F74 merged - release lane claim, tick backlog` |
| `store(<category>):` | A committed run's canonical artifacts | `store(chips.merchant-gpu): 2026-07-05 daily cycle #1 of 2 - gate-clean on the current stack` |
| `test(<scope>):` | Test-only change | `test(F56/F62): corpus-error test uses 2026-13 not 2026/06` |
| `chore(<scope>):` | Tooling/config, non-doctrine | `chore(claude): session-hygiene config from 10-day friction audit` |
| `refactor(<scope>):` | No behavior change | `refactor(publisher): F31 identity moved to shared module (F63 surface prep)` |
| `plan:` (no scope) | A one-off planning note, not tied to feat/fix | `plan: Task 3 handler reads REGISTRY_PATH at call time (T2 review follow-up)` |
| `Merge branch '<name>': <summary>` | Lane/feature merge to main | `Merge branch 'f74-cycle-log': cycle-plan journal clobber guard (F74)` |

Nearly every commit carries a trailing `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
trailer — keep it when authoring commits in this repo. Scopes are usually an F-id (`F63`), a
sub-project tag (`5-1`, `4-4c`), a lane letter (`B`, `C`), or a module/feature name (`evals`,
`web-reach`, `handoff`) — pick whichever most precisely names what changed.

## 6. README staleness policy (this skill's ruling)

**`readme.md` is updated at milestones only — `docs/superpowers/HANDOFF.md` + git are live truth,
always.** A "milestone" here means: a category ships live end-to-end, a phase in `docs/roadmap.md`
closes, or a frozen-core migration lands. Do not refresh the README on every commit; do not treat
its numbers as current between milestones. When you *do* refresh it, update at minimum: the suite
count, the F-range closed, the scorecard/category count, and any category's runnable-vs-live
status using the honest phrasing from §1 ("runnable-per-pins, never yet run live") rather than a
flat "runnable" or "not runnable." The staleness itself is not a bug to silently fix in passing —
call it out in the commit message (`docs(readme): refresh at <milestone> - was N days/M commits
stale`) so the next reader knows this was a deliberate, dated act, not a continuous truth.

## Common mistakes

- **Quoting a founding doc (`category-agent-guide.md`, `ai-market-state-map.md`) as current
  behavior.** They are pre-implementation design concepts; check §1's supersession table first.
- **Trusting a backlog checkbox alone**, in either direction — unchecked-but-merged (F56/57/58/
  59/61/63/68) and checked-but-not-fully-done (F44/START-HERE) both occur in this repo right now.
- **Onboarding a new session via `START-HERE.md`** — it will teach a dead OAuth backend and tell
  you the code doesn't exist yet.
- **Treating HANDOFF's lower sections as actionable** — they are historical strata, kept for
  archaeology, not a queue.
- **Silently picking a side on a live charter contradiction** — the Part 37 deferred-list case was
  reconciled 2026-07-06 by a maintainer ruling (state the shipped reality); the *next* such gap needs
  the same — surface it and get the ruling, don't quietly rewrite doctrine to suit your change.
- **Letting internal vocabulary (gate/Finding/brain/corroboration) leak into outward brief prose**
  — the reader is a TSMC executive, not another engineer on this repo.
- **Inventing a synonym for a bands.py or rating-anchors.md word** ("robust," "resilient" for a
  rating) instead of using the closed five-word vocabulary.
- **Silently "fixing" the README** instead of treating a refresh as a dated, deliberate,
  commit-logged act at a real milestone.

## Maintaining this skill library itself

This 16-skill library is itself now a doc of record and should be held to the same discipline it
teaches:

- **Date-stamp every volatile fact** (counts, statuses, HEAD hashes) at the point you verified it,
  and say what commit/date you verified it against — never state a count without one.
- **Every skill file ends with a "Provenance and maintenance" section** (see below) naming the
  verification date, the commit the author verified against, and a re-run command for every
  volatile claim in the file.
- **One fact, one home.** If a fact is owned by a sibling skill (see the table in §"When to use"),
  cross-reference it by skill name — do not restate it, and especially do not restate it
  *differently* (two skills disagreeing about the same fact is worse than one skill being silent).
- **Label unproven/open things as open or candidate**, explicitly, in the skill text itself —
  do not let a skill's confident tone imply something is settled when the repo's own docs mark it
  open (F71–F76, the eval-gate power question).

## Provenance and maintenance

Verified 2026-07-06 against `main @ 1a9eb33ec2db1bdb640079d3c200711b69c59525` (working tree clean
at verification time). The original 10-agent discovery sweep this library is built from was taken
2026-07-05 at `a8ec757` — the repo has moved substantially since (F74 merged, HANDOFF advanced,
CLAUDE.md committed); treat `a8ec757` as historical context only, not current state.

Re-verification commands, one per volatile fact class in this file:

```bash
# HEAD / working tree
git rev-parse HEAD && git status --short

# Suite baseline (README says 417/3 - confirm current)
.venv/Scripts/python -m pytest -q | tail -3

# Indicator count (17, not 31)
.venv/Scripts/python -c "import json; d=json.load(open('registry/indicators.json')); print(len(d['indicators']))"

# D6 overlay flip still in effect
grep -n '"D6"' registry/indicators.json | head -1

# Confidence enum still words-only
grep -n 'level: Literal' gpu_agent/schema/finding.py

# Checkbox staleness set (re-run for each id; compare to git log --grep)
grep -n '^- \[.\] \*\*F5[6-9]\|^- \[.\] \*\*F6[13]\|^- \[.\] \*\*F68' docs/fix-backlog.md

# START-HERE.md fossil status (only commit should be its creation, unless someone has since fixed it)
git log --oneline -- docs/superpowers/START-HERE.md

# Part 37 corroboration reconciliation held (reconciled 2026-07-06; expect the "shipped/still deferred" pair)
grep -n "staged multi-source corroboration\|Still deferred (by decision)" docs/agent-swarm-charter.md

# frontier-closed store status (should still be absent + ungitignored)
ls store/models.frontier-closed 2>/dev/null; grep -n "models.frontier-closed" .gitignore

# HANDOFF top section (always re-read fresh; do not trust any cached copy, including this file's quote)
sed -n '1,30p' docs/superpowers/HANDOFF.md

# Commit scope-prefix survey (re-sample if conventions drift)
git log --format="%s" --all | grep -oE "^[a-z]+(\([a-zA-Z0-9./_-]+\))?[!:]" | sort | uniq -c | sort -rn | head -20
```
