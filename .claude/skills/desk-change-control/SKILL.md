---
name: desk-change-control
description: Use when changing anything in the GPU Category Agent repo and unsure of the path - touching gate.py/scoring.py/schema/prompts/registry/manifests; tests/test_evals_baseline_pin.py suddenly red; an eval FAIL verdict; a fix-backlog checkbox contradicting git log; tempted to revert, hand-edit baseline.json or a brain answer, reorder F-items, or resurrect rejected ideas (SEC-EDGAR, scraper benchmarks); planning waves/lanes/worktrees or a Part-33 migration; a branch at "awaiting user merge go" or BLOCKED-on-user.
---

# Desk Change Control

## Overview

Every change in this repo is **classified before it is made**; the class — not the size of the diff — determines the path, the gates, and who approves. The gates' own records (eval baseline, brain answers, store artifacts, run journals) are never edited to make a gate pass.

## When to use / When NOT to use

| Situation | Go to |
|---|---|
| You are about to change code, data, prompts, or doctrine and need the correct path | **this skill** |
| You need to actually run the eval flow the gate demands | repo skill `run-eval` (mechanics), `desk-validation-and-qa` (evidence standards, fixture families) |
| You need to run a live/demo cycle or commit run artifacts | `desk-run-and-operate` |
| You hit a bug or failing test and don't yet know why | `desk-debugging-playbook` |
| You want the full story behind an incident named here | `desk-failure-archaeology` |
| You want WHY the frozen surface is frozen | `desk-architecture-contract` |
| You are working the F74/F71/F75/F72 cluster | `gate-integrity-campaign` |
| You need the catalog of flags/env gates/registry knobs | `desk-config-and-flags` |
| You are writing the migration doc / run-notes / HANDOFF text itself | `desk-docs-and-writing` (templates, house style) |
| You want to challenge a locked decision with new evidence | `desk-research-methodology` (evidence bar, adversarial refutation) |

## 1. The change taxonomy — classify FIRST

Jargon: **F-item** = a numbered entry in `docs/fix-backlog.md` (F1–F76 as of 2026-07-05), the repo's only defect/feature ledger. **Frozen core** = the contract surface listed below that changes only via versioned migrations (charter Part 33). **The pin** = `tests/test_evals_baseline_pin.py`, a SHA-256 hash of every emitted brain-prompt bundle, compared against `fixtures/evals/baseline.json`.

| Class | What it covers | Path | The incident behind the rule |
|---|---|---|---|
| **DATA** | `registry/*.json` weights/thresholds, `manifests/*.json`, assignments, same-role `registry/web-reach-tools.json` entries, taxonomy constituents | Edit + tests + normal commit. **Then re-run the pin test anyway** — registry text feeds emitted prompts | F27 proved the seam: `models.frontier-closed` became runnable as a config-only diff (commit b743ee9, 2026-07-02). Trap: the `.gitignore` store whitelist is category-hardcoded (`!store/chips.merchant-gpu/` — `.gitignore:7-15`); a new category's scorecards would land in an IGNORED dir. A "data-only" category add is not data-only. |
| **ORDINARY CODE** | Everything not in the frozen list and not prompt-emitting: `report.py`, `brief.py`, CLI surface, gathering, wiki, tests, scripts | Lane path (§5): own worktree, TDD, full suite green, review, await user merge | The 2026-07-02 review shipped ~40 fixes this way in one day without breaking main (Waves 0–2, integration commits f1c0835, d933b7e) |
| **FROZEN-CORE** | `gate.py`, `scoring.py`, `schema/*` (Finding schema, six dimensions, rating scale), `judgment/briefing.py`, `judge.py` aggregation, `pipeline.py`, `JsonStore` (list: `docs/roadmap.md` "Standing constraints") | **Part-33 versioned migration ONLY** — §3 and `references/part33-migration-playbook.md`. User approval is part of the shape | Contract v1.2 exists because the live store held 20 future-dated findings and 20 registry-contradicting sides that the old gate admitted (`docs/migrations/2026-07-contract-v1.2.md` §"Would the stored 2026-06 findings pass"). Piecemeal edits to a shared contract were never allowed a first time |
| **PROMPT** | ANY byte change to an emitted prompt — including whitespace, persona defaults, vocab ordering, and **registry label/text changes** | The pin goes red → run-eval flow + governed rebaseline (§4). Never hand-edit `fixtures/evals/baseline.json` (maintainer-confirmed, 2026-07-05) | F62's `observed=` vintage tag — two words of prompt context — triggered two full eval FAILs and a user decision before it could ship (commit b9301e8). Byte-level sensitivity is the design, not an accident |
| **DOCTRINE** | `docs/agent-swarm-charter.md` amendments, binding skill prose (`run-cycle`, `gather-category`, `run-eval`), `docs/roadmap.md` constraints | Feature path (§5) + user approval; amendments must reconcile the Parts they touch | Worked example of the reconcile obligation: for weeks Part 37's closing line said a flat "Not yet: hard corroboration" while the F63 amendment ~60 lines above shipped the *staged* corroboration step — the amendment never revisited its Part's other sentences. Reconciled 2026-07-06 (maintainer ruling: state the shipped reality) — the deferred list now says the staged step shipped (F63/F2e) and only the **full** Part 26 requirement remains deferred. Lesson: when you amend a Part, grep the rest of it for language your change now contradicts |

Two classes at once → the **stricter path wins** (a registry rename is DATA + PROMPT: it ships with its eval re-gate). Store/ artifacts are not "changes" — they are run outputs (append-only, never hand-edited); see `desk-run-and-operate`.

## 2. Classification procedure

Run from repo root, PowerShell 5.1 (all commands below are PowerShell-safe unless marked bash):

1. **Frozen check** — does the diff touch any file in the roadmap frozen list? `git diff --name-only` vs the list in `docs/roadmap.md` (search "Standing constraints"). Yes → FROZEN-CORE.
2. **Prompt check** — after the edit: `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`. Red → PROMPT (the failure message lists which seam drifted). This is the gate working, not a broken test.
3. **Doctrine check** — does it change what the charter, roadmap constraints, or a binding SKILL.md *instructs*? Yes → DOCTRINE.
4. **Data check** — diff confined to `registry/`, `manifests/`, `fixtures/asg.*`? → DATA (still do step 2).
5. Else → ORDINARY CODE.

**Escalate to the user (stop, write it up, wait) when:** the change is FROZEN-CORE or DOCTRINE; it touches anything on the rejected list (§9); it would reorder the locked F-sequence (§6); an eval verdict is FAIL (§4); or two instances may own the same files (see `CLAUDE.md` multi-instance rules).

## 3. Frozen-core changes: the Part-33 migration shape

Two worked precedents exist — copy their shape exactly. Full walk-through with the shadow-run tables and the hand-computation transcript: `references/part33-migration-playbook.md`.

| | Contract v1.2 (2026-07-02) | Contract v1.3 (2026-07-04) |
|---|---|---|
| Scope | 14 rules (F2a–e, F3, F7, F8, F9, F16, F17, F21, F36, F37) + D6 price-overlay flip | Exactly ONE rule: gate F2e gains the ≥3-distinct-publishers exception |
| schemaVersion | 1.1 → 1.2 (extraction stamps changed) | **Stays 1.2** — stated explicitly ("no schema field changed") |
| Doc | `docs/migrations/2026-07-contract-v1.2.md` | `docs/migrations/2026-07-contract-v1.3.md` |
| Approval | "user-approved 2026-07-02" in the doc | "user-approved 2026-07-04 in the F63 design" |
| Commit marker | one coupled worktree `fix/contract-v1.2` | `feat(gate)!:` breaking-change marker (bfd6571) |

Required artifacts for migration #3 (all of them, even for a one-rule change — v1.3 proves the minimal form still carries the full shape):

- [ ] **User approval recorded** — a migration is never AFK-defaulted.
- [ ] **ONE coupled migration** — "Frozen-contract items ship as one versioned migration, never piecemeal" (`docs/fix-backlog.md:11-13`).
- [ ] **Migration doc** in `docs/migrations/` — one line per rule change by F-id; an explicit schemaVersion decision *either way*; a "Deliberately unchanged" section.
- [ ] **Shadow-run** — old vs new math over the SAME stored findings, **no store writes**, diff table in the doc (precedent: `scripts/shadow_run_v12.py`).
- [ ] **Replay** — recompute stored scorecards as NEW appended store versions with `provenance.replayOf`; originals byte-unchanged; **replay re-runs MATH, never re-gates history** (precedent: `scripts/replay_v12.py`, v1..v6 → v7..v12).
- [ ] **Golden fixtures regenerated once + independent hand computation** in the commit message — commit 859ac35 hand-computes every DMI/SMI contribution term and states "Regenerated file matches exactly". A regeneration without the hand check is a self-graded exam.
- [ ] Full suite green; pin state re-checked (if prompts also moved, §4 applies too).
- [ ] Opus-class review on the contract diff at merge time (observed wave protocol, `docs/fix-backlog.md:528-530`).

## 4. Prompt changes: the eval gate as change control

Mechanics live in the repo `run-eval` skill; what belongs HERE is the governance:

- **Red pin = stop sign, not a broken test.** The unlock is the run-eval flow (re-dispatch brains + graders over the 18-case golden set, 3-replicate verdict) followed by `gpu-agent eval rebaseline --runs <d1> <d2> <d3> --verdict <verdict.json>`. The old `--out` form is gone; `--force` exists but requires `--reason` and a recorded justification (`gpu_agent/cli.py:1077-1078` as of the F74-merged tree, 2026-07-06 — re-grep before citing: `grep -n -- "--force\|--reason" gpu_agent/cli.py`, since cli.py's line numbers shift with every merge, most recently the F74 merge's ~35-line insertion).
- **Hand-editing `fixtures/evals/baseline.json` is forbidden** (maintainer-confirmed 2026-07-05), as is hand-editing any brain answer or recorded fixture — a rejected answer is re-dispatched with the verbatim violation text appended. Zero hand-edits across every documented run.
- **FAIL means STOP and write a `docs(eval)` run-notes commit.** Then the human — not the session — chooses between: `--force` rebaseline with reason / iterate the prompt / more replications. Verbatim doctrine, commit b9301e8: "Per pre-committed disposition: STOP (no retry-until-green), baseline pin stays red, decision is the user's."
- **"Retry until green" is forbidden.** The one time the bar itself was wrong (F63 failed twice against F62's lucky single-run incumbent), the response was to *rebuild the bar* (eval-v2: 3-replicate mean − ε, charter Part 24 amendment, commit 9f891c9) — not to force past it. Both FAILs were committed as run-notes (b9301e8, 345fc31) with pre-committed dispositions; that record is why the next session could diagnose noise instead of re-fighting blind.
- **Honesty label (F73, open):** the eval-v2 gate has never demonstrably caught a real regression, and its margins (F63 passed extract by 0.042) sit inside documented same-prompt noise (6.25–7.50 swings). Treat marginal verdicts as noise events — but that is an argument for fixing gate power (F73), **never** a license to bypass the gate.

## 5. Execution models: lane vs feature

**Wave/lane model** (fixes — `docs/fix-backlog.md:488-538`):

1. One short plan per lane in `docs/superpowers/plans/`; lanes own **disjoint files** (the lane map assigns exclusive ownership).
2. One git worktree per lane under `.worktrees/<name>` (gitignored; one shared root `.venv`, never per-worktree venvs). Max 5 concurrent lanes.
3. Dispatch all lane agents in ONE message; each executes its lane sequentially: TDD, self-review, commit per task.
4. **Merge gate is sequential**: rebase each lane onto the accumulated result; **full suite green before the next merge**; task-review each lane's diff at merge time.
5. Validation gate after a big wave = a real live cycle (the F46 precedent).

**Lane claiming** (multi-instance): claim in `docs/superpowers/HANDOFF.md` before touching anything — worktree name, branch, base commit, the exact files claimed, and explicit NON-claims. Worked example: the F74 claim (HANDOFF, 2026-07-05) claims `gpu_agent/cli.py` (`_cycle_plan` only) + run-cycle SKILL step 1 + two test files, and explicitly does NOT claim `store/cycle-log.json` because the in-flight daily run owns it.

**Feature path** (anything doctrine-shaped, frozen-core-shaped, or new machinery — F4/F5/F6/F62/F63/F67/F69/F70 all went this way): `superpowers:brainstorming` → spec → plan → subagent-driven development, as its own sub-project on its own branch. "Do not let a lane agent improvise these" (`docs/fix-backlog.md:533-538`).

**Long-lived branches** merge main INTO the branch before the final merge, re-gate the eval on the branch, then stop (precedents: 57be83c, a84be52, ef52790).

## 6. The F-item lifecycle

**Minting.** F-items are born from review events and live-run incidents, in batches:

| Batch | Origin | Section |
|---|---|---|
| F1–F48 | 2026-07-02 full-repo review (3 parallel deep reviews + live-scorecard inspection) | `docs/fix-backlog.md:1` |
| F49–F56, F67–F71 | births between reviews — validation gates, integration gates, first live firings (each entry carries a "born from…" note; F71 born on the sufficiency gate's first live cycle) | inline |
| F57–F66 | 2026-07-03 freshness & exec-gap review (section header says F57–F65; F66 sits inside it) | line 255 |
| F72–F76 | 2026-07-05 outside-eyes state review | line 556 |

F-numbers are backlog IDs, **not chronology** (F6 executed after F55; F50/F51 listed before F49 by design).

**Sequencing is user-locked.** "Sequence (user-approved 2026-07-03 — do not reorder): F62 → F63 → F57/F58/F59 → F60 → F64 → F65 → F66" (`docs/roadmap.md`, Phase 1). The F72–F76 priority ordering is a "lean (user to confirm)": F74 immediately, F72 with/after F71, F75 before any unattended loop (`docs/fix-backlog.md:556-565`). Do not reorder either list; do not promote the lean to a decision.

**Closing — CHECKBOX STALENESS WARNING.** The backlog's checkboxes lag reality. As of 2026-07-05 (main @ 639c00d) these are merged to main but still show `- [ ]`: **F56 (core), F57, F58, F59, F61, F63, F68** (merges 72261a4, e173ebc, 017b592; F61 subsumed by F67 per HANDOFF). Never trust a checkbox without reconciling:

```powershell
git log --oneline --grep="F57"                  # find the closing/merge commit
git merge-base --is-ancestor 72261a4 main; $?   # True = it is on main
```

Status lookup order: **HANDOFF top block → git log --grep=F\<nn\> → the backlog entry text** (rich and accurate on content, unreliable on checkbox state). Residuals can hide behind "merged": F68a landed but its wiring is deferred; F56's second cosmetic minor may be unclosed — read the entry text, not just the box. Full doc trust order is owned by `desk-docs-and-writing`.

## 7. Fix forward, never revert (maintainer-confirmed)

Zero revert/backout commits in 480 commits across all branches (verified 2026-07-05 @ 639c00d). When something shipped wrong: mint an F-item, fix it in a lane or sub-project, record the closure. Even the strongest case — the F46 cycle that mislabeled its scorecard `2026-06-v13` — was corrected by removing the mislabeled artifact, re-running the cycle, and shipping F50 as a Wave-2 fix with the story recorded (`docs/fix-backlog.md:187-191`), not by `git revert`. Corrections to stored history go through migration replays (§3) that APPEND new versions; originals stay byte-unchanged.

## 8. Merge discipline — one confirmed-law claim, one observed-practice claim (don't bundle them)

These two claims carry **different confidence levels** and must not be presented under one label:

- **"Only the user merges to main" — observed practice, strong evidence, NOT confirmed as binding law by the maintainer.** Evidence: "merges to main stay human" (commit 6a5534c); merge-awaiting messages ("merge awaits user go", 4f6c9d1; "awaiting final review + user merge go", adf21e8); three commits carry **BLOCKED-on-user** verbatim (b9301e8, 345fc31, 6b75d33). An agent's end state for a branch is: suite counts recorded, eval re-gated green, review findings addressed, HANDOFF updated — then STOP. **BLOCKED-on-user is a real, legitimate state**, not a failure — F63 sat in it twice while eval-v2 was designed.
- **AFK-default labeling + never-merge-under-AFK — CONFIRMED, user-level WRITTEN LAW**, not just observed practice: `~/.claude/CLAUDE.md` (per-machine, outside this repo) states verbatim, under "Decisions while I'm AFK": *"record the decision as 'AFK-default' — never as 'user-approved' or 'user-decided'... Never merge to main, push a merge, or delete branches under an AFK-default."* This is stronger than the repo's own historical practice (commit a0dfe41: "all picks AFK-defaulted to recommendations per the F52-F54 precedent; relitigable before implementation") — that repo history is corroborating evidence, but the rule itself is now written law at the operator level. F76b exists because these labels are not yet uniform *inside the repo's own docs* (backlog/HANDOFF/specs) — when you see "user-approved" in a spec, check whether it cites an actual user answer.
- Historical example (no longer live): the F74 fix went through exactly this discipline — built on `.worktrees/f74-cycle-log` (3613ede, suite 1063/4 green), then merged same-day at `257cf1b` (2026-07-05, user go), backlog ticked at `1a9eb33`. The worktree/branch are now deleted entirely (not retained) — this is now a precedent for the merge-discipline pattern, not a branch to go look for.

## 9. The rejected-ideas list (user-locked — do not resurrect)

"Considered and REJECTED (user-approved 2026-07-03 — do not resurrect without new evidence)" (`docs/fix-backlog.md:293-299`):

1. **SEC EDGAR structured pipeline / sec-api.io spend** — deepens the filings strength while the leading pipeline is the weakness; only F59's tier-classifier fix survived.
2. **Search-API/scraper-stack benchmark (Tavily/Exa/Firecrawl…)** — the headline gap is aim + doctrine, not fetch tech; "revisit only if fetch failures remain the binding constraint after F57/F58."

The parenthetical revisit conditions are the ONLY lawful re-entry, and re-opening runs through `desk-research-methodology`'s evidence bar plus a user decision. `docs/roadmap.md` restates the lock: "REJECTED items stay rejected." Related do-not list: never "fix" `gpu_agent/llm/anthropic_api.py` or `ClaudeCodeClient` into a live API path — the SDK file is a dormant, doctrine-forbidden alternate seam (see `desk-architecture-contract`).

## 10. Non-negotiables (with status labels)

| Rule | Status | Why / incident |
|---|---|---|
| Never hand-edit brain outputs or recorded answers; re-dispatch with the verbatim violation | **Maintainer-confirmed 2026-07-05** | An edited answer is an ungated judgment reaching canonical — the exact thing the frozen brain exists to prevent. Held live: 2026-07-03 cycle, 5 re-dispatches, zero hand edits |
| Never hand-edit `fixtures/evals/baseline.json` | **Maintainer-confirmed 2026-07-05** | The baseline is the gate's memory; editing it is grading your own exam. Test docstring says it verbatim |
| Fix forward, never revert | **Maintainer-confirmed 2026-07-05** | Zero reverts in 480 commits; corrections are F-items + appended versions (§7) |
| Frozen core changes only as Part-33 migrations | Doc-bound (`docs/fix-backlog.md:11-13`, `docs/roadmap.md` standing constraints, charter Part 33) | v1.2's justification section shows what un-gated contract drift had already let into the store |
| No retry-until-green on the eval gate | Doctrine, commit b9301e8 | Retrying a noisy gate until it passes converts the gate into a random-number generator |
| Rejections stay rejected; F-sequence not reordered | User-approved 2026-07-03 | Both are user locks; only the user unlocks them |
| Only the user merges to main | **Observed practice** (strong git/doc evidence, not confirmed law) | §8 evidence |
| AFK decisions labeled AFK-default, never merged under that label | **Confirmed, user-level written law** (`~/.claude/CLAUDE.md`, per-machine, not in this repo) | §8 |

## Common mistakes

- **Trusting backlog checkboxes** — seven are stale right now (§6). Reconcile with git before stating any F-item status.
- **Treating run-cycle's bypass prose as durable doctrine** — `.claude/skills/run-cycle/SKILL.md` (main, ~lines 147–158) still teaches "neither check ever blocks a scorecard… run with `--no-voice-lint` or `--no-sufficiency`". That text is F75's named removal target; do not cite it as policy, and expect it to change when the F74/F75 lanes merge.
- **"It's just a registry label"** — registry text feeds emitted prompts; the pin flips; you now own a PROMPT change with its full eval cycle.
- **"Adding category #2 is data-only"** — the `.gitignore` store whitelist must be amended first or the scorecards land in an ignored directory silently.
- **Reverting, or amending stored artifacts in place** — both violate fix-forward and append-only; use F-items and replays.
- **Skipping the migration doc for a "tiny" gate tweak** — v1.3 changed one rule and still shipped a full migration doc with a "Deliberately unchanged" section.
- **Deleting "stale-looking" worktrees** — `.worktrees/{eval-v2, f62-flagship-store, f63-corroboration}` are merged but deliberately retained: their gitignored `work/` holds the raw eval replicate data behind the committed baseline. Never `git clean` anywhere in this repo.
- **Quoting charter Part 37's pre-2026-07-06 flat "Not yet: hard corroboration" line** — it was reconciled to say the staged step shipped (F63/F2e); only the full Part 26 requirement is still deferred (§1, DOCTRINE row).
- **Recording an away-user default as "user-approved"** — label it AFK-default and relitigable (§8).

## Provenance and maintenance

Authored 2026-07-05 against the library baseline main @ a8ec757; every fact re-verified same day at main @ 639c00d (4 commits later: F74 lane claimed + built on `.worktrees/f74-cycle-log` @ 3613ede unmerged; daily #1 committed d9cfb3f; working tree clean). Charter/backlog line numbers drift — re-check before quoting. Re-verify volatile facts:

| Fact class | One-liner (repo root) |
|---|---|
| HEAD / tree / worktrees | `git log --oneline -1; git status --short; git worktree list` |
| Stale-checkbox list | `git log --oneline --grep="F63"` then `git merge-base --is-ancestor <hash> main; $?` per item vs `Select-String '^- \[' docs/fix-backlog.md` |
| Frozen-core file list | `Select-String -Context 0,3 'Frozen contract' docs/roadmap.md` |
| Migration count/shape | `ls docs/migrations/` (exactly 2 files as of 2026-07-05) |
| Eval bars & baseline schema | `.venv/Scripts/python -c "import json; b=json.load(open('fixtures/evals/baseline.json')); print(b['schemaVersion'], b['seamMeans'], b['epsilon'])"` (v2; means 6.75/7.5833/6.00; eps 0.3125/0.25/0.50) |
| Pin still armed | `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q` |
| F75 target prose still in run-cycle | `Select-String 'no-sufficiency' .claude/skills/run-cycle/SKILL.md` |
| Zero reverts / commit count | `git log --oneline --all --grep=revert -i` (empty) ; bash: `git log --oneline --all \| wc -l` (480 @ 639c00d) |
| Rejected list unchanged | `Select-String 'REJECTED' docs/fix-backlog.md docs/roadmap.md` |
| F72–F76 lean still unconfirmed | `Select-String 'user to confirm' docs/fix-backlog.md` |
| Suite size | `.venv/Scripts/python -m pytest --collect-only -q` (1063 collected @ 639c00d; expect 3–4 skips when run) |
