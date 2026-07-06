---
name: desk-research-methodology
description: Use when deciding whether a diagnosis or fix is actually right before shipping it; before running any eval, gate, or experiment (pre-commit the disposition first); when a hunch needs to become an F-item, a roadmap question, or a spec; when asking "has this been tried/rejected before", "is this a real regression or noise", "who is allowed to decide this"; when assigning or receiving an adversarial review/skeptic pass; or when an approval gate has timed out and a decision was made AFK.
---

# Desk Research Methodology

## Overview

The discipline that turns a hunch into an accepted result in this repo, in one sentence: **you
do not believe a mechanism because it is plausible — you believe it when it explains every
observation you have, including the ones that do not fit, you commit to what would make you
stop *before* you look at results, and you assign someone (or a separate pass) to try to kill it
before it ships.** This skill is the capstone of the 16-skill library: it also maps which of the
other 15 owns which fact, so read the division-of-labor table below before searching elsewhere.

## When to use / when NOT to use

Use this skill when: judging whether a diagnosis is real and not just plausible; writing down a
disposition before an eval/gate/experiment runs; deciding where a new idea belongs (F-item vs.
roadmap open question vs. a spec); assigning or receiving an adversarial review; deciding whether
a decision is yours to make or must escalate; or reasoning about an AFK-timed-out approval gate.

Do NOT use this skill for (go to the named sibling instead):
- The mechanics of the eval verdict ladder, fixture families, or hash-pin — **desk-validation-and-qa**.
- Wave/lane execution mechanics, Part-33 migration procedure, F-item checkbox bureaucracy —
  **desk-change-control**.
- F-item/migration-doc/run-notes/HANDOFF templates and house style — **desk-docs-and-writing**.
- The full chronicle of past incidents (symptom → root cause → evidence → status) —
  **desk-failure-archaeology**.
- Replicate-noise math, independent hand computation, shadow-run/replay recipes —
  **desk-proof-and-analysis-toolkit**.
- Domain rating/Finding/corroboration semantics — **market-state-reference**.
- Executing the F74→F71→F75→F72 campaign itself — **gate-integrity-campaign**.
- Claims for an audience outside this repo, novelty/SOTA framing — **desk-external-positioning**.
- Open research problems and their first steps — **desk-research-frontier**.

---

## 1. The evidence bar: one mechanism, every observation, survives a kill attempt

A diagnosis is not accepted here because it sounds right. It is accepted when **one mechanism
explains every observation you have — including the negatives — and it survives someone
deliberately trying to break it.**

**Positive precedent — F62 (2026-07-04).** The judge eval seam failed twice with a *consistent
signature* (all 8 fresh generations scored `sensitivity-differentiation = 1` for the same named
reason), which licensed a **falsifiable prediction made before running anything**: amend the
prompt, predict the criterion moves 1→2. It did, on all four fresh generations — confirmation by
a result nobody had seen yet, not a post-hoc story. This is what makes F62 the evidence-bar
worked example: a uniform deficit signature plus a pre-registered prediction, not "the eval
failed twice." Full symptom→root-cause→evidence chronicle: **desk-failure-archaeology** fight #8;
numeric detail: `references/worked-examples.md#f62`.

**Counter-example — F27 (2026-07-02).** A plausible-sounding mechanism ("empty weights → zero
indices" for `models.frontier-closed`) sat in the backlog as ground truth, unchecked against the
code, until a fix lane looked and found it **stale and wrong** — registry-weight fallback meant
indices were never zero. This is the evidence-bar's counter-example: a diagnosis can survive into
a "DONE" checkbox without ever being checked against actual runtime behavior. Full incident:
**desk-failure-archaeology** fight #4; source citation: `references/worked-examples.md#f27`.

**Checklist before you accept your own diagnosis:**
1. List every observation, especially the ones your mechanism does *not* obviously explain yet.
2. Ask what your mechanism predicts about something you have not looked at — then look.
3. Name the strongest competing mechanism and what experiment would distinguish them — run it.
4. Assign an adversarial pass (fresh subagent / different session / fresh-context read) whose
   only job is to break the diagnosis before you act on it (§5).
5. If you cannot state what evidence would prove you wrong, you do not have a mechanism yet —
   you have a story.

---

## 2. Pre-committed dispositions: decide before you know

Verbatim, commit `b9301e8` (F62 eval run notes): *"Per pre-committed disposition: **STOP (no
retry-until-green)**, baseline pin stays red, decision is the user's: `--force` rebaseline with
reason / iterate judge prompt / more replications."* This sentence was written **before**
`record-grade` ran attempt 2. That ordering is the whole discipline: the disposition is not a
post-hoc rationalization of whatever number came back — it is a commitment made blind.

The mechanical form under eval-v2 (PASS / marginal-fail→one replication→two-run-mean /
hard-fail→stop / invalid-run→fix the grader-or-brain not the score) is **desk-validation-and-qa's**
territory — this skill only owns the *discipline* of writing the disposition down first. The
same discipline generalizes past evals: before any live cycle, experiment, or adversarial
review, write what result makes you stop, what makes you proceed, and who decides the marginal
case — before you have the result in hand. "Retry until green" is forbidden doctrine here in
every context, not only eval seams.

---

## 3. The idea lifecycle, end to end

```
hunch → mint (F-item | roadmap open question) → experiment → [feature-shaped: spec → plan → SDD]
      → gate (suite + eval + shadow-run/replay for frozen core) → adopted | documented retirement
```

**Minting rule — which bucket?**

| Shape | Goes to | Precedent |
|---|---|---|
| Bounded, one file-ownership lane, no new doctrine/machinery | An F-item under a wave/lane (`docs/fix-backlog.md`) | F1–F51, F56–F61, F71–F77 |
| Touches doctrine, frozen core (`gate.py`/`scoring.py`/schema), or introduces new machinery | An F-item tagged **Features** (`docs/fix-backlog.md`, header *"Features (per repo convention: brainstorming → spec → plan, own sub-project — not lane work)"*), then `superpowers:brainstorming` → spec → plan → `superpowers:subagent-driven-development` | F4/F5/F6/F62/F63/F67/F69/F70, eval-v2 |
| A strategic/product choice only the user can make (category #2, repo rename, cost tolerance, decision-area set…) | `docs/roadmap.md` §"Open strategic questions" — **not** an F-item; do not pick it for the user | Roadmap open questions 1–8 |

The wave/lane worktree mechanics, merge order, and F-item checkbox procedure are
**desk-change-control**'s; this skill only owns *how you decide which bucket a hunch goes in*.

**Experiment stage.** Recorded/replay seams (`--emit-prompt` / `--recorded`, `RecordedClient`)
make iteration $0 — a candidate prompt or fixture change costs nothing to re-run against frozen
gates. `work/<run-dir>/` is the lab notebook: gitignored, never `git clean`d, preserved even
after a branch merges (three retained worktrees carry raw eval replicate data behind the
*committed* baseline right now — `.worktrees/eval-v2`, `.worktrees/f62-flagship-store`,
`.worktrees/f63-corroboration`). The actual noise-math, hand-computation, and shadow-run/replay
recipes for this stage are **desk-proof-and-analysis-toolkit**'s; this skill only says: iterate
here, cheaply, before you propose anything.

**Spec/plan/SDD stage (feature-shaped work only).** `docs/superpowers/` carries the full trail —
specs and plans for essentially every feature this repo has (verify current counts: `ls
docs/superpowers/specs | wc -l` / `ls docs/superpowers/plans | wc -l`; both directories exist and
are nearly all built-and-merged, the acknowledged exception being the still-DRAFT
`2026-07-04-autonomous-dev-loop-design.md`, gated on user review that has not happened). The
standing rule when a spec and its plan conflict during implementation: **the spec wins**
(exercised in sp5-2, per `docs/superpowers/HANDOFF.md`).

**Gate stage.** Full suite green + (if brain-prompt-touching) an eval verdict PASS + (if
frozen-core) a Part-33 migration with shadow-run + replay. Mechanics: **desk-validation-and-qa**
and **desk-change-control**.

**Adopted.** A human merges (never an agent — see §7); the F-item's checkbox flips (in
principle — checkboxes lag reality; see §Common mistakes and **desk-docs-and-writing**'s trust
order); if the change was doctrinal, a charter Part gets an amendment, not a silent edit. Two
worked precedents: the eval-v2 amendment to Part 24 (*"The incumbent bar is the mean of three
stored replicate runs minus a replicate-derived tolerance… (eval-v2, 2026-07-05)"*) and F63's
amendment to Part 37 (the ≥3-distinct-publisher corroboration exception). A charter amendment is
how "adopted" becomes durable, not just merged.

**Documented retirement.** Rejection is a first-class, recorded outcome — never a silent drop.
Two standing precedents, both explicitly **user-approved 2026-07-03, do not resurrect without
new evidence** (`docs/fix-backlog.md`): the SEC-EDGAR / `sec-api.io` structured pipeline, and the
search-API/scraper-stack benchmark (Tavily/Exa/Firecrawl). Both were re-recommended, independently
and with real evidence behind them, by the 2026-07-03 external best-practices research pass — and
stayed rejected anyway (§4). A stalled draft is a distinct third status, neither adopted nor
retired: the autonomous-dev-loop spec is complete, fully AFK-authored, and has never passed its
own user-review gate — it is dormant, not abandoned and not shipped. Do not treat "spec exists"
as "adopted."

---

## 4. Where good ideas historically came from here (mine before you invent)

| Source | What it produced | Evidence |
|---|---|---|
| **Live-run failures** | An idea, gate, or code path meets its first real disagreement on the very first live run, not in review. F52 (finding-id collision on the first real sp5 cycle), F71 (anchor-bound vs. sufficiency-gate deadlock on the sufficiency gate's *first* live firing) | `docs/fix-backlog.md` F52/F71 |
| **Eval fights forcing a structural fix over a retry** | F63 failed the eval gate twice against a bar that was itself a lucky high draw (F62 attempt 3). Rather than force past it, **eval-v2 (the replicate baseline) was designed and built in one day** (2026-07-04→05) and F63 then passed on its own merit. The flagship example of "the bar was wrong, so rebuild the bar" beating "force past it." | commits `345fc31`→`c0d5dd2`→`017b592` |
| **Deliberately scheduled outside-eyes reviews** | Two review events, not one: F1–F51 from *"three parallel deep reviews (core pipeline, temporal store/brief, ops/docs)"* (2026-07-02), and F72–F76 from a fresh-context review the user explicitly asked for by posing the question *"what are we least confident about / what am I missing"* (2026-07-05). F74 — active, urgent data loss sitting in the working tree — was found this way, not by the instance that had been living inside the dirty tree the whole time. **Lesson: schedule this question deliberately; do not wait for it to surface itself.** | `docs/fix-backlog.md` intro + "From the 2026-07-05 outside-eyes state review" header |
| **External research passes, read for method not just conclusions** | `docs/2026-07-03-agent-best-practices-research.md`: a deep-research harness verified 25 of 105 candidate claims, confidence-labeled, and named its own §7 refuted-claims list (never resurrect: MAST per-category percentages, Zep/Graphiti benchmark wins, the +10.8pp deterministic-aggregation figure, Finnhub archive depth). The epistemics lesson is in what happened next, not the claims themselves: see next row. | `references/worked-examples.md#research-pass` |
| **A well-sourced recommendation is not an authorization** | That same research pass recommended SEC-EDGAR sourcing and a search-API/scraper benchmark. Both were REJECTED anyway (§3) — the user weighed fit and cost, not just factual correctness. Verified ≠ approved. | `docs/fix-backlog.md` REJECTED note |
| **Blind ablation as a live idea-generation instrument** *(new since the 2026-07-05 discovery baseline — observed 2026-07-06)* | `docs/ablation-2026-07/`: the desk's real committed-store render vs. two fresh web-only baselines (an RSS digest, a one-shot deep-research pass), randomly lettered, scored by the user against a **pre-registered rubric** (decision-usefulness / insight / currency / trustworthiness with 2 citation spot-checks each) *before* the answer key was opened. Produced a real actionable finding (**F77**, brief hierarchy) and a validated **null result** — the desk's substance already wins; the gap is presentation only, not gathering or judgment. A null result reached this rigorously is exactly as valuable as a positive one. | `docs/ablation-2026-07/SCORING.md`, `ANSWER-KEY.md`; verdict in `docs/action-items.md` |

---

## 5. Adversarial refutation as an assignment, not a hope

Do not ask "does this look right?" of the person who wrote it. **Assign someone — a fresh
subagent, a different pass, a different context — the explicit job of finding out it's wrong.**
A green test suite is necessary, not sufficient.

**Precedent — F74's "8-angle review" (commit `9a5f9b2`, 2026-07-05).** After the F74 clobber-guard
fix already had a green suite, a dedicated adversarial pass was run over the just-shipped code
and found **4 confirmed findings** the implementer had missed: hand-copied key sets that could
silently drift from the model, null/mis-typed containers crashing instead of refusing cleanly, a
Windows BOM able to disguise a bare plan as a real journal, and a directory-as-`--out` path
raising a raw `PermissionError` instead of refusing cleanly. The fix commit records: *"Empirical
verify pass confirmed all four code findings before fixing."* — the review didn't just guess,
it reproduced each failure before trusting the finding.

**Precedent — frozen negative eval cases.** Four negative cases are re-graded on every eval run
specifically so a miscalibrated or rubber-stamping grader gets caught (calibration ceiling:
every negative case's total must stay ≤ 4/8). This is adversarial refutation built into the gate
itself, not a one-off review — mechanics are **desk-validation-and-qa**'s.

**Precedent — F38 (independent generations).** Judgment samples and re-dispatches come from
*separate* subagent generations specifically because "a single subagent producing all samples
yields correlated votes and fake self-consistency" (`run-cycle` SKILL.md). Self-consistency you
generated yourself is not evidence of correctness.

**Practical instruction for a Sonnet session finishing a fix:** do not mark it done off your own
review. Either dispatch a second pass with an explicit "find why this is wrong, then verify each
finding empirically before reporting it" framing (`code-review` skill, or `superpowers:receiving-code-review`
if the feedback is already in hand), or run an angle-review pass modeled on F74's before calling
anything shipped.

---

## 6. The AFK/provenance rule — observed, then partly codified

**The wound (F76b, open):** decisions were recorded as `"user-approved"` in specs and the backlog
that were actually taken under an "AFK precedent" — the user away at a question gate, an agent
proceeding on the recommended option. The label made real user sign-off indistinguishable from
an agent's best guess. F52–F54's spec flagged this; the 2026-07-05 outside-eyes review logged it
as **F76** (coordination-substrate integrity) — **still open** as of this writing: its acceptance
criteria (standardized labels *inside* the backlog/handoff/specs themselves) are not met.

**What changed since the 2026-07-05 discovery baseline (observed 2026-07-06):** the rule is now
written, verbatim, at the user level — `~/.claude/CLAUDE.md` (per-machine, **not** part of this
git repo, will not exist on a fresh clone or another machine):

> *"If an AskUserQuestion or approval gate times out, you may proceed on best judgment for
> reversible work, but record the decision as 'AFK-default' — never as 'user-approved' or
> 'user-decided'. Re-surface every AFK-default decision when I return and in any handoff doc.
> Never merge to main, push a merge, or delete branches under an AFK-default. Park the work
> committed on its branch and wait."*

Treat this as **required practice today**, but do not claim F76 is closed — the repo's own
committed `CLAUDE.md` (`29584d9`) does not carry this text, and the backlog item explicitly wants
the standard applied inside the repo's own documents, which has not been done. This is itself a
clean instance of the idea lifecycle (§3): observed wound → informal fix at one layer → the
formal fix (F76's acceptance criteria) still pending.

**What this means in practice:** if an approval gate times out, proceed only on reversible work,
label the decision `AFK-default` (not `user-approved`) everywhere you record it, and never merge,
push a merge, or delete a branch under that label — that class of action waits for an actual
answer (§7).

---

## 7. Escalation — what you must not decide alone

| Decision | Who decides | Route to |
|---|---|---|
| Merge a branch to `main` | Human only — every merge commit in this repo's history (14 as of this writing, `git log --all --merges --oneline`) is a human act; branches park at "awaiting user merge go" / "BLOCKED-on-user" and wait | **desk-change-control** |
| Change frozen core (`gate.py`, `scoring.py`, Finding schema, six dimensions, rating scale, `judge.py` aggregation, `pipeline.py`, `JsonStore`) | User-approved Part-33 migration, drafted then approved — never silent | **desk-change-control**, **desk-architecture-contract** |
| Amend charter doctrine (a Part's "never/always" rule) | Amendment with a note, not a silent edit | **desk-change-control** |
| Reorder the user-locked F-sequence, or resurrect a REJECTED idea | Don't — sequencing and rejections are user-approved and stand until new evidence *and* new user approval | **desk-change-control** |
| A red eval pin / FAIL verdict | STOP, write the run-notes commit, the disposition (force-with-reason / iterate prompt / more replications / structural fix) is the user's call — never retry-until-green | **desk-validation-and-qa** |
| Hand-edit a brain answer, a recorded fixture, or `baseline.json` | Never, by anyone, ever — re-dispatch or rebaseline are the only unlocks; there is no escalation path because the answer is always "don't" | **desk-validation-and-qa**, **desk-debugging-playbook** |
| An AFK-timed-out approval gate | Proceed only on reversible work, label `AFK-default`, never merge/push-merge/delete a branch | this skill, §6 |
| A roadmap "open strategic question" (category #2 choice, repo rename, cost tolerance, decision-area expansion…) | Explicitly user-owned; a good guess is not a substitute for the user's answer | **desk-docs-and-writing** (roadmap doc), **desk-change-control** |

---

## Capstone: division of labor across the 16-skill library

One fact, one home. If you are about to restate something below, go use that skill instead.

| Skill | Owns |
|---|---|
| **desk-change-control** | How changes are classified/gated/reviewed: frozen surface, Part-33 migrations, wave/lane model, eval-gate governance, F-item lifecycle mechanics, fix-forward rule, non-negotiables + rationale + incident |
| **desk-debugging-playbook** | Symptom→triage tables for this project's failure modes; traps with their stories; discriminating experiments |
| **desk-failure-archaeology** | The full chronicle: every investigation/dead end/rejected fix as symptom → root cause → evidence → status |
| **desk-architecture-contract** | Load-bearing design decisions + why, the invariants, the seams, deferred stubs, known-weak points |
| **market-state-reference** | Domain theory: dimensions, Finding semantics, indices math, rating anchors, corroboration, thesis rules, indicator registry, paywall doctrine |
| **desk-config-and-flags** | Every config axis: CLI flags/verbs, env gates, registry knobs, gitignore whitelist, bypass flags; how to add one |
| **desk-build-and-env** | Recreate the environment from scratch; Windows traps; per-machine invisible state; web-reach bootstrap |
| **desk-run-and-operate** | Operator's map: routes to run-cycle/gather-category/run-eval, dispatch choreography, artifact landing map, commit discipline, preflight, demo-vs-live |
| **desk-diagnostics-and-tooling** | How to measure instead of eyeball: reconciliation commands, store/wiki/dedup inspection, seam-noise measurement; ships scripts |
| **desk-validation-and-qa** | What counts as evidence; the three fixture families; hash-pin discipline; suite baseline; how to add tests; the eval verdict ladder |
| **desk-docs-and-writing** | Docs of record, trust order between them, templates (F-item, migration doc, run-notes, HANDOFF), house style |
| **desk-external-positioning** | What's novel vs. known, proof obligations before claiming, reproducibility standard, do-not-claim list |
| **gate-integrity-campaign** | The executable decision-gated campaign for the hardest live problem cluster: F74 (done) → F71 → F75 → F72 |
| **desk-proof-and-analysis-toolkit** | First-principles analysis recipes: replicate/noise math, independent hand computation, shadow-run/replay, gate-power proofs, each with a worked example |
| **desk-research-frontier** | Open problems where this project could advance SOTA, with first-3-steps and falsifiable milestones |
| **desk-research-methodology** *(this skill)* | The discipline itself: evidence bar, pre-committed dispositions, idea lifecycle, adversarial refutation, escalation |

---

## Common mistakes

- Accepting a diagnosis because it is plausible, without checking it against the one observation
  that does not obviously fit (F27's "empty weights → zero indices").
- Deciding what a marginal result means *after* seeing it, instead of writing the disposition
  down first (the opposite of `b9301e8`'s discipline).
- Retrying an eval, gate, or experiment until it goes green instead of stopping at the
  pre-committed disposition — "retry until green" is forbidden doctrine here, in every context.
- Reviewing your own fix and calling it shipped — a green suite is not an adversarial pass (F74
  shipped a green-suite fix that still had 4 confirmed defects until the 8-angle review ran).
- Treating `user-approved` and `AFK-default` as interchangeable labels, or inferring the user
  decided something because an agent's recommended option was taken while they were away.
- Resurrecting a documented-rejected idea because a new, independently well-sourced pass
  re-recommends it — a correct recommendation is not the same as an authorized one; it takes new
  evidence *and* new user approval to reopen a rejection, not just a second citation.
- Deciding a merge, a doctrine amendment, an F-sequence reorder, or a roadmap open question
  yourself because it "seemed obviously right" — see the escalation table (§7).
- Treating a spec's existence as adoption — the autonomous-dev-loop spec is complete and has sat
  un-reviewed since 2026-07-04; a spec is not shipped until its own review gate is passed.
- Skipping the step most diagnoses skip: asking what your mechanism predicts about something you
  have *not yet checked*, then actually checking it.

---

## Provenance and maintenance

Authored 2026-07-06, `main @ f7c83f0` (1066 passed / 4 skipped, verified live this session). The
Phase-1 discovery baseline this skill was drafted from was `main @ a8ec757` (2026-07-05) — the
repo has moved substantially since: F74 (§ examples above) is now merged (`257cf1b`), a new F77
was born from the ablation study, and the working tree was clean at authoring time. **§1's F62/F27
precedents trimmed 2026-07-06** to point at `desk-failure-archaeology` (the chronicle's designated
owner) instead of re-narrating the incidents independently — this skill keeps only the
evidence-bar lesson each one illustrates. Re-verify before trusting any number in this file:

| Fact class | Re-verification command |
|---|---|
| Current HEAD / working-tree cleanliness | `git log --oneline -1` / `git status --short` |
| F-item checkbox states (F71/F72/F73/F75/F76/F77 open; F74 done) | `grep -n "^\- \[x\]\|^\- \[ \]" docs/fix-backlog.md` |
| Suite baseline count | `.venv/Scripts/python -m pytest -q \| tail -3` |
| Charter Part line numbers (24, 25, 33, 36, 37) | `grep -n "^## Part" docs/agent-swarm-charter.md` |
| Specs/plans trail size | `ls docs/superpowers/specs \| wc -l` / `ls docs/superpowers/plans \| wc -l` |
| Autonomous-dev-loop spec status | `grep -n "Status" docs/superpowers/specs/2026-07-04-autonomous-dev-loop-design.md` |
| run-cycle's whole-run bypass wording (F75 target) | `grep -n "no-sufficiency\|no-voice-lint" .claude/skills/run-cycle/SKILL.md` |
| The AFK-default rule's written form (per-machine, not in this repo) | `Get-Content $env:USERPROFILE\.claude\CLAUDE.md` (PowerShell) — absent on a fresh clone/other machine |
| Ablation verdict / F77 origin | `docs/action-items.md` §"Verdict — blind baseline ablation 2026-07"; `docs/ablation-2026-07/` |
| Retained worktrees (lab-notebook evidence) | `git worktree list` |

See `references/worked-examples.md` for the fuller narrative behind each cited precedent (F62,
F27, the eval-v2-in-a-day timeline, F74's 8-angle review, the blind ablation, and the 2026-07-03
research pass's epistemics lesson).
