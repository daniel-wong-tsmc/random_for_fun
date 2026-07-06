# Annotated templates — desk-docs-and-writing

Full fill-in-the-blank versions of the four templates summarized in SKILL.md §3, with inline
commentary on *why* each field exists (derived from real, verified instances — see SKILL.md for
the source quotes). Use the compact skeletons in SKILL.md for quick reference; come here when
you're filling one in for real and want the reasoning behind each field.

---

## 1. New F-item entry (`docs/fix-backlog.md`)

```markdown
- [ ] **F<n> — <one-line symptom, present tense, no editorializing>.** <2-4 sentences: WHERE it
  lives (a file:line citation or an observed behavior with evidence — not "somewhere in judge.py"),
  WHY it matters (say explicitly whether it is must-have: corrupts numbers/judgments, violates a
  binding doctrine rule, loses data, lets fabricated/injected content reach a rating — or
  should-have: scale-out readiness, robustness, hygiene, presentation). If the fix is non-trivial,
  number the steps so the entry is checkable against the eventual diff before the diff exists.
  Acceptance: <a condition someone could mechanically check — "clobber scenario test-pinned", not
  "looks better">. *(<Lane letter> | Wave N | feature-track: brainstorm→spec→plan→SDD)*
```

Field-by-field:

- **One-line symptom, present tense.** Written as a standing fact about the system ("post-run
  writer clobbers the session-authored cycle log"), not a past-tense incident report ("a writer
  clobbered the log yesterday"). It should still read true the moment before the fix lands.
- **Evidence citation.** A reviewer six months from now, with zero memory of the incident, must be
  able to go to that file:line and see the thing being described. If you cannot point at a
  file:line or a reproducible command, the entry is a hunch, not a backlog item — say so
  explicitly ("not yet reproduced; reported by X") rather than inventing a citation.
- **Must-have vs should-have.** This is not a vibe call — check it against the four must-have
  criteria (numbers/judgments corruption, binding-doctrine violation, data loss, fabrication/
  injection reaching a rating). If none apply, it is should-have, and it will be worked later.
  Mislabeling wastes triage time in both directions.
- **Numbered fix steps** (for anything non-trivial). This is what let F74's entry — written before
  the fix existed — become directly checkable against the merged diff. An entry that only
  describes the symptom, with no fix shape, forces the fixer to re-derive scope from scratch.
- **Acceptance.** Must be something you could fail. "The guard test exists and is pinned",
  "the offending writer is named in the fix commit" — both mechanically checkable. "It's better
  now" is not an acceptance criterion.
- **Tag.** Either a lane letter (bounded, file-ownership-scoped, sequential-within-lane fix — see
  `desk-change-control` for what qualifies) or an explicit feature-track note (anything touching
  doctrine, frozen core, or new machinery goes through brainstorm→spec→plan→SDD as its own
  sub-project, never improvised inside a lane).

---

## 2. Migration doc skeleton (`docs/migrations/<date>-contract-v<N>.md`)

```markdown
# Contract v<N> migration — <date>

The <ordinal> sanctioned frozen-core migration (charter Part 33; user-approved <date>[, in
<link to the design spec that got the approval, if one exists>]). <One sentence stating whether
schemaVersion moves and, if not, why — a migration is still a migration even with schemaVersion
unchanged, as long as it touches gate.py/scoring.py/the Finding schema/the six dimensions/the
rating scale>.

## Rule change(s)

- **F<id>** — <one line: the old behavior, an arrow, the new behavior, and the file/function that
  enforces it>. Error text should be quoted verbatim if it changed (so someone grepping stderr
  later can find this doc).

## Deliberately unchanged

- <Name the things a reviewer might reasonably assume also moved, and say explicitly that they did
  not, with a one-clause reason.> This section exists because migrations are read defensively —
  a reader who does NOT see something addressed here will assume it silently changed, which is
  worse than a redundant "no, this didn't move" line.

## Companion doctrine (same branch, not frozen-core)

- <Non-frozen code or doctrine that rides in on the same branch as the migration — e.g. a new
  gate that consumes the migrated rule, a charter amendment recording the change, a new registry
  knob.> Keep this section separate from "Rule change(s)" even though it ships together: frozen
  vs non-frozen is the whole point of gating migrations in the first place, and blurring the two
  in the doc undoes the distinction the doc exists to preserve.
```

Notes from the two real precedents:

- v1.2 bundled 14 rule changes into ONE migration event because they were user-approved as a
  single coupled stream (contract v1.2 lanes A+B) — a migration doc can cover many rules at once
  if they were approved and shipped together; it should never be split into "one doc per rule"
  after the fact.
- v1.3 shows the minimal legal form: exactly one rule, `schemaVersion` unchanged. Don't assume a
  migration needs to be large to count, and don't assume `schemaVersion` must bump — bump it only
  when an actual schema *field* changed.
- Both precedents include a "would old/stored data pass under the new rule?" style section
  (v1.2's shadow-run + replay). That mechanic (recompute stored history under new math without
  re-gating it) is owned by `desk-validation-and-qa` / `desk-proof-and-analysis-toolkit` — link to
  it, don't reimplement the explanation here.

---

## 3. Eval run-notes skeleton (`docs/superpowers/eval-notes/<date>-<label>-run-notes.md`)

```markdown
# Eval run <date> (<F-id or label>) — <one line: what triggered the re-gate>

Trigger: <which SYSTEM prompt(s) changed and in which commit(s) — the hash-pin test names the
seams affected; say which ones and why>.

Procedure: .claude/skills/run-eval/SKILL.md; run root: work/<dir>/ (name the worktree/branch if
this ran on a feature branch, not main).

Incumbents (current baseline): extract <x> / judge <y> / thesis <z>.

## Pre-committed disposition (recorded BEFORE any record-grade)

Write this section FIRST, before dispatching a single grader, and do not edit it afterward no
matter what the results say. This is the entire point of the pattern: the disposition table is
evidence that the verdict wasn't reverse-engineered from a result you wanted.

PASS -> <rebaseline command with --reason, what gets committed, what suite check gates the
commit>.
Marginal-fail -> <the replication rule: exactly one replication, decided how>.
Hard-fail (or N fails) -> STOP: <name exactly what stays red, what does NOT happen — "no
rebaseline, no --force">. **NOT retry-until-green.**

## In-run observations (if any recur across cases)

<Note systematic failure modes as they happen, even mid-run — e.g. "the brain counts publishers
quoted INSIDE one document as corroboration" — these become fix-backlog candidates below,
independent of whether the run ultimately passes or fails.>

## Gate + grade-wave setup

<record-brain attempt(s): clean count, F38 re-dispatches by case id and the verbatim violation
each one got; any transport-normalization notes (fenced JSON stripped, extra keys observed);
frozen-negative grade carry-over and its byte-identity check.>

## Verdict

<seam scores vs bars, explicit PASS/FAIL per seam, per-case score breakdown.>

## Diagnosis (per the pre-committed disposition, before any further run)

For every point lost, answer explicitly: does this trace to the prompt change under test, or is
it coverage/grader-strictness variance that would show up on ANY rerun? Cite the specific case
and the specific evidence — "extract-05 completeness 0, same case that scored lowest in every
prior run" is a diagnosis; "seems noisy" is not.

## Disposition executed

<State what actually happened, matched explicitly against the pre-committed table — "both runs
failed -> per the pre-committed disposition the run STOPS here" — so a reader can verify the
outcome followed the rule rather than a judgment call made after the fact.>

## Cross-run analysis (if more than one run happened)

<What do the multiple draws tell you about the incumbent bar itself, independent of the prompt
change under test? This is where "the bar is noisy" claims get their evidence.>

## User options (if the disposition reaches BLOCKED-on-user)

<Enumerate the real choices — force-rebaseline on a judgment call, more replications, an
infrastructure change, or hold — and say which is fastest/most expensive/most rigorous. Do not
pick one; that decision is the user's.>

## Fix-backlog candidates surfaced by this run

<Each concrete prompt/registry fix this run surfaced, as its own future eval-gated change — never
folded into the current pass/fail silently. Even a run that ultimately PASSES can surface these.>
```

Why this shape, not a shorter one: every fight this repo has actually won (F62 twice, F63 twice)
was won because the losing attempt was fully written up this way — the next session could read
the diagnosis and design eval-v2 directly from it, instead of re-running the same fight blind.
A run-notes file that only records the final PASS/FAIL number throws away the only part that
makes the next attempt smarter.

---

## 4. HANDOFF top-section skeleton

```markdown
# HANDOFF — GPU Category Agent (resume point: <one line, present tense, the state RIGHT NOW>)

- **Date:** <date> (<AM/PM or session marker — HANDOFF gets rewritten multiple times a day when
  multiple instances are active; the marker disambiguates which write is newest>)
- **Repo:** <url>
- <State-of-the-world bullet(s): what ran, on which commit (name the store/merge hash), which
  gate(s) passed/failed and HOW (no bypass? which bypass, named, never buried?), counts that
  matter (re-dispatches, promotions, new proposals), and any KNOWN GAP logged rather than hidden
  (name the F-item if one exists for it)>
- <Anything still OPEN that blocks the next milestone, named explicitly, so the next session
  doesn't have to rediscover it>
- **NEXT:** <the single next action; unambiguous enough that a fresh session with zero other
  context could start immediately>

## HISTORICAL — <prior state description> (superseded by the section above)

<The previous top section, demoted here — either verbatim or tightly summarized. Never delete a
prior top section; the "trust the title block, verify below" doctrine depends on lower sections
existing as an honest record, not a rewritten one.>

## ⚠ CONCURRENT-INSTANCE COORDINATION (still live)

<A roster, one line per F-item/lane currently or recently in flight: branch name, worktree path,
sentinel filename (`.superpowers/handoffs/<lane>-DONE.md`), merge hash if merged, and one line of
"operational changes every future run must know" if the lane changed a shared procedure (run-cycle
steps, a CLI flag's meaning, a new tripwire test). This section is what stops two concurrent
instances from re-doing or colliding over the same lane.>
```

The mechanical procedure that PRODUCES this file each session (verify pushed, gather live state
via git/pytest/ledgers, prepend rather than overwrite, label every timed-out gate decision
"AFK-default" and surface it at the top, commit and push) belongs to the user-level `desk-handoff`
skill — this file is only the content contract that procedure's output must satisfy.
