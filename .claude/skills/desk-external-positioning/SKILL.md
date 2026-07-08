---
name: desk-external-positioning
description: Use when drafting anything meant for an audience outside this repo — a paper, README, blog post, pitch deck, demo script, or any claim about this project's novelty, "beyond SOTA," calibration, autonomy, or scale; when asked "is this novel," "what can we claim," "how do we compare to X," or "can we say we validated/proved Y"; before citing readme.md build-status numbers, docs/superpowers/START-HERE.md, or the best-practices research doc externally; before any TSMC-branded or public exposure of this repo.
---

# Desk External Positioning

## Overview

This desk earns external claims the same way it earns internal ones: nothing ships without a
written, checkable "how do you know that?" (the charter's own closing test, `docs/agent-swarm-charter.md:1803-1804`).
Every novelty or "beyond SOTA" claim below has a **named closest-known-art comparison** and a
**named proof obligation that is not yet satisfied** — the honest position is almost always
"architecturally distinct, not yet validated," not "proven."

## When to use / when NOT to use

**Use when** you are writing or reviewing anything that leaves the repo's own operating context:
a paper draft, a README rewrite, a demo for a non-technical audience, a claim comparing this
project to other agent/eval/forecasting systems, or a decision about what to say (or not say)
publicly.

**Do NOT use for:**
- Internal docs, HANDOFF, run-notes, migration docs → `desk-docs-and-writing` (templates, trust order, house style).
- Deciding whether a research idea is worth pursuing, or running the idea lifecycle → `desk-research-frontier` (open problems, milestones) / `desk-research-methodology` (evidence bar, adversarial refutation, idea lifecycle).
- The actual gate-integrity fixes (F71/F72/F74/F75) → `gate-integrity-campaign`.
- Domain semantics (what a Finding/anchor/thesis *means*) → `market-state-reference`.
- What counts as evidence internally, fixture families, hash-pins → `desk-validation-and-qa`.

## 1. What is genuinely novel here — and its closest known art

State novelty claims in this shape: **[mechanism] vs [closest known art] — [what this repo adds] —
[what is NOT yet proven]**. Never drop the last column.

| # | Mechanism (this repo) | Closest known art | What this repo adds | Not yet proven |
|---|---|---|---|---|
| 1 | Evidence-gated LLM judgment behind a deterministic pre-commit gate (Part 7): every rating is bounded — never set — by a code-computed anchor from the same registry data the LLM must cite | LLM-as-judge evals; Anthropic's own "gates" + orchestrator-workers taxonomy (`docs/2026-07-03-agent-best-practices-research.md` §1, confidence high 3-0); schema/guardrail frameworks (Instructor, Guardrails-style output validation) | Guardrail frameworks typically check shape/toxicity/PII. This gate checks a **domain invariant against the model's own cited evidence** — "no rating may contradict its cited measured anchor" (Part 7) — computed independently in code, not asserted by the model | The gate can **deadlock against itself**: the anchor bound and the F63 evidence-sufficiency gate contradicted each other on the sufficiency gate's first live firing, resolved by a whole-run bypass (F71, open). A gate that must be bypassed to complete its first real contest is not yet a proof of soundness |
| 2 | Session-as-brain: `--emit-prompt` / `--recorded` seam — the coordinating Claude Code session itself is the LLM backend; no API key, no token metering, byte-deterministic prompts, $0 replay forever | Recorded/replay ("cassette") testing patterns for LLM calls; human-in-the-loop agent designs where a person executes a step | Using the **coding assistant's own session** as the production inference path (not a test double) turns every historical run into a $0, byte-exact replay via a hash-pinned prompt bundle (`tests/test_evals_baseline_pin.py`) rather than a stored raw response cassette | Proven at the scale of **one** live category (`chips.merchant-gpu`). `models.frontier-closed` is config-runnable but has never produced a live scorecard (no `store/models.frontier-closed/` directory, confirmed 2026-07-06) — the seam is not yet proven to generalize |
| 3 | Replicate-based eval governance with pre-committed dispositions: 3-replicate baseline, bar = mean − ε (ε from measured noise), marginal-fail earns exactly one more replication, per-case crater floor, disposition written **before** the result is seen | Standard single-run CI eval gates; pre-registered analysis plans (clinical-trial-style pre-registration) applied to an LLM prompt-regression gate | Brings pre-registration discipline to a domain (LLM judge quality) where most projects still gate on one noisy run — built in one day specifically because a single-run bar failed twice on lucky/unlucky draws (F62, F63 sagas — full story in `desk-failure-archaeology`) | **F73, open: the eval-v2 gate has never demonstrably caught a real regression.** Margins observed so far (F63 passed extract by 0.042 against a documented 6.25–7.50 same-prompt swing) sit inside noise. Do not call this "a validated eval harness" |
| 4 | Append-only, vintage-honest market memory: temporal wiki (`log.jsonl`) + thesis book, `observedAt`/`capturedAt` split to block look-ahead, immutable versioned scorecards, a designed (not yet wired) Brier hook | Bi-temporal knowledge graphs (Zep/Graphiti — explicitly the architecture reference the desk borrowed, per the best-practices doc); forecasting-platform track records (the ForecastBench/superforecaster Brier literature cited in that same doc) | Append-only + vintage-honest by construction, gated at write time by the same Part-7 checklist as everything else — not bolted on after the fact | **F64, open: zero realized-outcome Brier scoring exists in code today** (verified 2026-07-06: `Brier` appears only in docs, no hits in `gpu_agent/`). The schema intent exists (charter Part 12); the calibration number does not |
| 5 | Fix-forward governance culture: zero revert commits across 486 commits (verified 2026-07-06); corrections are F-items + Part-33 migration replays that append new versions, never edit history in place | Blameless-postmortem / SRE culture; "roll forward" CD philosophies | Applied unusually *consistently* to **data** as well as code — eval FAILs become committed `docs(eval)` run-notes (the losing attempt is the artifact), migrations replay math forward without re-gating history | This is a **discipline applied with rigor**, not an invention — claim "unusually consistent application, evidenced by git history," never "a new methodology" on its own |

## 2. What must be proven before each "beyond SOTA" claim

The maintainer's definition of "beyond SOTA" for this project has five pillars. None is satisfied
today (2026-07-06); each has a named, checkable gate.

| Pillar | Proof required | Status (2026-07-06) | Where the work lives |
|---|---|---|---|
| **Calibrated market judgment** (Brier) | F64's Brier-accrual half must exist in code and accumulate resolved outcomes over real triggers | **Open — zero realized-outcome scoring exists.** `grep -r Brier gpu_agent/` returns nothing; the concept is doc-only (charter Part 12, `docs/fix-backlog.md` F64) | `desk-research-frontier` (milestone) — this track is independent of the gate-integrity cluster |
| **Provably-gated autonomy** | F71 (anchor-vs-sufficiency precedence) + F75 (per-item bypass policy, no whole-run bypass flags) + F76 (coordination-substrate integrity) all closed, **and** the autonomous-dev-loop spec ratified by the user | **Open on all four.** F71/F72/F73/F75/F76 all unchecked in `docs/fix-backlog.md` (verified 2026-07-06); `docs/superpowers/specs/2026-07-04-autonomous-dev-loop-design.md` is still `Status: DRAFT — awaiting user review` (no implementation exists; `docs/superpowers/DEV-QUEUE.md` does not exist on disk) | `gate-integrity-campaign` (F74→F71→F75→F72 executable path) |
| **The methodology itself as a publishable pattern** | F73's gate-power proof: a seeded-regression canary showing the eval gate hard-fails a deliberately damaged prompt, plus a symmetric marginal band and pooled dispersion | **Open.** No seeded-regression canary exists; the gate's only track record is passing marginal (0.042-margin) re-gates, which is evidence of *noise tolerance*, not *discriminative power* | `desk-proof-and-analysis-toolkit` (gate-power proof recipe), `desk-validation-and-qa` (eval mechanics) |
| **Scale with fidelity** | A second category actually run live (not just config-runnable) + F24 (entity canonicalization) + F25 (wiki store scaling) closed | **Open.** `models.frontier-closed` has an assignment/manifest and scores config-only (F27, done 2026-07-02) but **no `store/models.frontier-closed/` directory exists** — it has never produced a live scorecard. F24/F25 both unchecked | `market-state-reference` (current single-desk reality), roadmap Phase 2 |
| **Gray-area critical thinking** (depth + broader market impact, not black-and-white rule-following) | No proxy exists yet in this codebase. **Falsifiable proxy candidates, honestly labeled candidate/open, not built:** (a) a **deferral-usage audit** — count and inspect anti-whipsaw `deferred` vs `applied` thesis judgments (`gpu_agent/thesis.py` rule-6 logic) as a signal the desk is declining to over-commit on thin evidence rather than always taking the confident-sounding path; (b) **dispersion-surfacing audits** — how often confidence/dispersion is honestly reported vs silently resolved; (c) the **episode-backtest half of Action Item 1** (`docs/action-items.md` "Half 2" — DeepSeek moment, CoWoS crunch, Ethernet-over-InfiniBand, etc.), still open, sitting in roadmap Phase 7 | **Candidate only — nothing built or measured.** Do not claim this pillar exists; the honest statement is "we have not yet defined how we would falsify a claim of good judgment here beyond rule compliance" | `desk-research-frontier` (this is exactly the shape of an open problem with a first-3-steps writeup) |

## 3. The do-not-claim list (hard table)

| Claim | Verdict | Why |
|---|---|---|
| "This project has no API/SDK path" (stated absolutely) | **Do not claim** | `gpu_agent/llm/anthropic_api.py` exists in code — an `AnthropicAPIClient` alternate backend, selectable via `factory.py`'s `backend='anthropic_api'`. It is **dormant and doctrine-forbidden for live use**, not absent. Say: "the live default path uses no API/SDK; a swappable alternate backend exists in code and is out of doctrine" |
| "We have a validated eval harness" | **Do not claim** | F73, open: the gate has never demonstrably caught a real regression. The only evidence is marginal passes inside documented noise |
| "The desk produces calibrated (Brier-scored) market judgment" | **Do not claim** | Zero realized-outcome scoring exists in code (F64, open). The schema intends it; nothing accrues it yet |
| "The desk runs autonomously" / "unattended" / any framing implying an unattended loop exists or is safe | **Do not claim** | The autonomous-dev-loop spec is DRAFT, unimplemented, awaiting user review; F71/F75/F76 (gate-deadlock, whole-run bypass, coordination integrity) are explicit, unclosed preconditions |
| "This scales to 34 categories" / "N desks are live" | **Do not claim** | Exactly **one** category (`chips.merchant-gpu`) has ever produced a live scorecard, as of 2026-07-06. `models.frontier-closed` is config-runnable, never run live. Layer and Main tiers are deferred stubs, not built |
| "Hard corroboration is enforced" | **Do not claim** | Charter Part 26's **full** hard corroboration + hard secondary-confidence cap remain deferred (Part 37 "Still deferred" list, reconciled 2026-07-06). What is live is only F63's *staged* 3-distinct-publisher bounded step — and F72 (open) shows even that step is exploitable by cross-domain wire syndication today |
| Anything from the best-practices research doc's §7 refuted list: MAST per-category percentages, Zep/Graphiti benchmark win numbers, the "+10.8pp deterministic-aggregation" effect, Finnhub archive-depth figures | **Do not claim** | `docs/2026-07-03-agent-best-practices-research.md` §7 verified these did not survive its own adversarial check — cite the *mechanisms*, never the retracted numbers |
| "We benchmarked and chose our search/scraper stack" | **Do not claim** | The same doc's §8 open question 1 states plainly: zero claims survived verification on this question; it needs a hands-on pass that was never done. Also: re-litigating a search-API/scraper-stack benchmark is a user-rejected idea (`docs/fix-backlog.md` "REJECTED... do not resurrect") |
| readme.md's build-status numbers (417 tests, "F1–F49", six scorecards) | **Do not cite externally** | Stale by roughly 650 tests and multiple F-batches as of 2026-07-06; verify live counts before citing any number (§ Provenance below) |
| docs/superpowers/START-HERE.md's onboarding claims (OAuth backend, "Next: write the code") | **Do not cite externally** | A 2026-06-22 fossil; the backend claim directly contradicts the shipped no-OAuth/no-SDK doctrine |
| Charter Part 37's corroboration status, presented loosely | **State it precisely** | Reconciled 2026-07-06: the deferred-list now says the *staged* 3-publisher step **shipped** (F63/F2e) and only the **full** Part 26 hard-corroboration + hard secondary-confidence cap remain deferred. Externally: "staged corroboration shipped; full hard corroboration not yet" — never collapse the two directions into "corroboration is/ isn't done" |

## 4. The reproducibility standard for any external artifact

**Replay-from-snapshot is existence.** This is the charter's own bar, stated twice: "A gather run
that can't be replayed from its saved snapshot did not happen" (Part 37) and "A cycle that can't be
replayed from its saved run-log did not happen" (Part 38). The external-facing corollary is
stricter: **a result someone outside this repo cannot replay from committed fixtures does not get
claimed.**

Concretely, before citing a result externally, name which reproducibility tier it sits in:

| Tier | What it is | $0 replayable by an outsider? |
|---|---|---|
| `fixtures/recorded/*` | Canned LLM answers for CLI-path demo replay | Yes — this is the tier to point external reviewers at first |
| `fixtures/evals/*` + `fixtures/evals/baseline.json` | The 18-case golden set + the eval-v2 baseline | Yes, mechanically (`gpu-agent eval emit-brain` etc. reconstruct the exact prompt bytes) — but the *baseline itself* is only n=3 replicates (F73 caveat above) |
| `fixtures/golden/*` | The deterministic scoring-path golden (pins `gate.py`/`scoring.py`/pipeline math) | Yes — pure code, no LLM involved |
| `store/chips.merchant-gpu/*` committed scorecards | Live run outputs | Only as **evidence of what happened**, not as a re-runnable proof — a live LLM dispatch is not literally re-executable byte-for-byte on demand (the emitted prompt is; a *fresh* subagent answer is not) |
| Anything in a gitignored `work/` dir, or uncommitted | Raw run scratch | **No.** Not citable. Not even internally durable — `docs/fix-backlog.md`'s F76 tracks exactly this risk (retained-worktree raw eval data with no registry) |

**Worked example of the standard in motion — now a citable result, with named limits:** the blind
baseline ablation assembled 2026-07-05 (`docs/ablation-2026-07/{A,B,C,SCORING,ANSWER-KEY}.md`,
commit `639c00d`) is the right *shape* for an external comparison — three artifacts on the same
scope (the desk's rendered brief vs an RSS-digest baseline vs a one-shot deep-research baseline,
both baselines web-only with zero repo context, citations verified web-only), randomly assigned,
scored blind against a pre-written rubric (decision-usefulness / insight-beyond-headlines /
currency / trustworthiness via 2 citation spot-checks / a forced single "keep" choice) before the
mapping was revealed. **It has since been scored: the user's verdict was recorded 2026-07-06**
(commit `f7c83f0`, "docs(ablation): record user verdict - desk won blind read on substance; F77
brief hierarchy"; verdict text in `docs/action-items.md` §"Verdict — blind baseline ablation
2026-07") — the desk won the blind read on substance/implications; every named deficit landed on
presentation only, now tracked as **F77** (brief hierarchy), not on gathering or judgment. This is
now citable evidence for the gray-area/depth axis specifically — but **do not generalize it into a
general "beats SOTA" claim**: it is one comparison, one reader, one date, against two cheap
web-only baselines (the same hedge `desk-research-frontier` applies to this same result). Cite it
as validating axis 5's *direction* (depth pays off), and as the *template* for how this desk
constructs an externally-defensible comparison — not as a repeatable benchmark result.

## 5. Presentation hygiene

- **Repo rename before TSMC-branded exposure.** This is an explicit, still-open user decision
  (`docs/roadmap.md` open strategic question #3: "still `random_for_fun`... must precede any
  TSMC-branded exposure (F48)"; `docs/superpowers/HANDOFF.md` carries the same line). F48 itself
  shipped an honest readme but explicitly left the rename as a user call. Do not publish anything
  TSMC-branded from a repo still named `random_for_fun`.
- **No internal jargon outward — this is now committed law, not just a norm.** `CLAUDE.md` (committed
  2026-07-05, `29584d9`): "Agent briefs are read by a non-technical executive persona: no
  AI/doctrine/internal jargon in output prose (run it through the stop-slop skill)." Anything
  written for an external reader should pass the same bar: no "F-item," "gate," "sufficiency,"
  "anchor-bound," "brain," or Part-numbers in the reader-facing text — those are this repo's
  internal vocabulary, not the reader's.
- **The charter's own closing test is the arbiter for any claim, internal or external:** "could a
  TSMC executive ask 'how do you know that?' and find the answer already written? If not, it does
  not ship." (`docs/agent-swarm-charter.md:1803-1804`.) Before a positioning claim ships, write down
  the answer to that question in the same document — if you can't, the claim isn't ready.

## Common mistakes

- **Claiming "no API/SDK path" as an absolute fact.** Say "the live default path" — the alternate backend exists in code (`gpu_agent/llm/anthropic_api.py`) and is inert-but-present, not deleted.
- **Treating a passing eval verdict as proof the gate works.** A pass inside documented noise (F73) is not evidence of discriminative power — it is the opposite; flag F73 every time an eval result is used as a quality claim.
- **Quoting the best-practices research doc's §7 refuted numbers** because they're sitting right next to the confirmed ones in the same table — always check the confidence/refuted column before citing anything from that doc.
- **Reading `docs/fix-backlog.md` checkboxes as ground truth for what's "done" before making a claim** — several stay unchecked long after merge (see `desk-change-control` §6 for the reconciliation procedure); a positioning claim built on a stale checkbox is a positioning claim built on nothing.
- **Treating the blind ablation as a general "beats SOTA" proof.** It IS scored now (2026-07-06, desk won on substance; deficits are presentation-only, F77) and is citable for the gray-area axis specifically — but it is one reader, one date, two cheap baselines. Re-verify its scoring status (`grep -n "Verdict" docs/action-items.md`) before citing, since this file may again lag a future re-scoring or follow-up ablation.
- **Overstating Part 37 corroboration in either direction.** The old internal contradiction was reconciled 2026-07-06; the precise, citable status is "staged 3-publisher corroboration shipped (F63/F2e); full Part 26 hard corroboration + hard secondary-confidence cap still deferred; F72 shows the staged step is syndication-exploitable today." Do not compress that to "corroboration is done" or "corroboration isn't built."
- **Copying suite counts, "F1–F49," or scorecard counts from readme.md** without re-running the check — that file is a known-stale snapshot (see Provenance table).
- **Proposing to resurrect the SEC-EDGAR or search/scraper-benchmark ideas as a positioning "next step"** — both are user-rejected (`docs/fix-backlog.md`); reopening either requires new evidence via `desk-research-methodology`, not a positioning doc.

## Provenance and maintenance

Authored 2026-07-06 against main @ `1a9eb33` (HEAD == `origin/main` at that time, working tree
clean apart from other agents' new skill directories in `.claude/skills/`); **§4's ablation-scoring
claim corrected 2026-07-06 after re-verifying against a later commit, `f7c83f0`**, which recorded
the user's verdict one commit after this file's original authoring point — the original text was
accurate at `1a9eb33` and stale within the same day. The Phase-1 discovery baseline this project
library was built from is main @ `a8ec757` (2026-07-05) — cited here only as historical context.
Since the discovery baseline: F74 (the cycle-log clobber) was fixed and merged (`257cf1b`,
backlog ticked `1a9eb33`); F71/F72/F73/F75/F76 remain open; the blind ablation was scored by the
user 2026-07-06 (`f7c83f0`), with F77 (brief hierarchy) minted from the result.

| Fact class | Re-verification command (repo root, PowerShell) |
|---|---|
| HEAD / tree state | `git log --oneline -1; git status --short` |
| F71/F72/F73/F74/F75/F76 checkbox + merge status | `Select-String '^\- \[.\] \*\*F7[1-6]' docs/fix-backlog.md` then `git log --oneline --grep="F<n>"` per item |
| Autonomous-dev-loop spec status | `Select-String '^\*\*Status' docs/superpowers/specs/2026-07-04-autonomous-dev-loop-design.md` (expect `DRAFT`) |
| Blind ablation scoring status | `Select-String 'Verdict' docs/action-items.md` (expect the scored verdict + F77) |
| Zero realized-outcome Brier scoring | bash: `grep -rn "Brier" gpu_agent/` (expect no hits outside comments, if any) |
| `anthropic_api.py` dormant-alternate status | `Select-String 'anthropic_api' gpu_agent/llm/factory.py` |
| `models.frontier-closed` never run live | `Test-Path store/models.frontier-closed` (expect `False`) |
| Charter Part 37 corroboration status (reconciled 2026-07-06) | `Select-String -Context 1,3 'Still deferred \(by decision\)' docs/agent-swarm-charter.md` (expect the "staged shipped / full deferred" pair; if it reverts to a flat "Not yet: hard corroboration" the reconciliation was lost) |
| readme.md staleness | `Select-String 'passed.*skipped' readme.md` vs `.venv\Scripts\python -m pytest --collect-only -q` (live count) |
| Repo-rename decision still open | `Select-String 'Repo rename' docs/roadmap.md docs/superpowers/HANDOFF.md` |
| Zero-revert claim | bash: `git log --oneline --all -i --grep=revert --grep=backout --grep=abandon` (expect empty); `git log --oneline --all \| wc -l` for current commit count |
| CLAUDE.md no-jargon rule still committed | `git log --oneline -- CLAUDE.md` (expect `29584d9` present); `Select-String 'non-technical executive persona' CLAUDE.md` |
