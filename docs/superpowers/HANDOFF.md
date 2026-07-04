# HANDOFF — GPU Category Agent (resume point: F67 + F6 eval harness both MERGED to main; next = F6 Task 10 live baseline, then F62)

- **Date:** 2026-07-04
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **Suite 910 passed / 5 skipped — verified on merged main @ `87f281a` and pushed. The 2 extra
  skips are the F6 baseline-pin tests; they arm automatically when `fixtures/evals/baseline.json`
  lands (Task 10).**

## ⚠ CONCURRENT-INSTANCE COORDINATION — RESOLVED

F67 is DONE (merged `b0e8061`, completion handoff `.superpowers/handoffs/output-engineering-DONE.md`).
The output-surface hold is LIFTED. F61 was subsumed by F67 (staleness banner shipped in the renderer).
The F6 branch was merged `87f281a` (user-approved 2026-07-04); worktree and branch deleted.

## IMMEDIATE NEXT TASK — F6 Task 10: the live eval baseline (UNBLOCKED, prompts are post-F67)

Follow `.claude/skills/run-eval/SKILL.md` — ~15 brain + ~20 grader tool-less Opus dispatches →
`eval rebaseline` → commit `fixtures/evals/baseline.json` (arms the hash-pin regression gate that
every prompt change in F57/F58/F62/F63 depends on). The plan's Task 10 checklist:
`docs/superpowers/plans/2026-07-04-f6-eval-harness.md` (bootstrap expectations, calibration
invariant, human spot-check before rebaseline). Watch item from review: negative case
extract-2026-07-90 is anchor-forced (ceiling 2/8) — verify calibration holds on this first run;
thesis seam-mean is coarse (2 positives, steps of 1.0). Execution ledger with per-task review
outcomes + deferred minors: `.superpowers/sdd/f6/progress.md`.

## Newest state (newest first)
  - **F6 SECOND HALF MERGED (`87f281a`, user-approved; 15 branch commits; suite 910/5 verified
    on merged main and pushed).** Remaining: Task 10 only (see IMMEDIATE NEXT TASK).
    `gpu_agent/evals/` (cases/rubric/emit/prompt_hash/harness) + `eval` CLI
    (emit-brain/record-brain/emit-grade/record-grade/rebaseline) + 18-case golden set curated from
    the real July cycles (provenance spot-verified byte-exact; 4 anchor-decidable negatives) +
    fixture-health tests + hash-pin regression-gate test (skips until baseline.json exists) +
    `.claude/skills/run-eval` skill. Spec `docs/superpowers/specs/2026-07-04-f6-eval-harness-design.md`,
    plan + Task-10 checklist `docs/superpowers/plans/2026-07-04-f6-eval-harness.md`. Post-F67
    alignment done on-branch: main merged in (`57be83c`), eval judge brain-gate mirrors the live
    voice lint, 4 pre-F67 judge positives re-pinned gateOutcome=reject (documented). Comparison
    rule: per-seam mean ≥ incumbent, TIES PASS. **Decision provenance: user approved scope/
    architecture/spec + chose subagent-driven execution; user was AFK at the finish-branch gate —
    merge deliberately left for the user (see pending-decision section).**
  - **F67 output contract MERGED (`b0e8061`, suite 873/3 on main).** Reader vocabulary layer
    (`gpu_agent/reader.py` + `registry/acronyms.json`), voice lint fail-loud on `judge --recorded`
    + `pipeline --recorded-judge` (`--no-voice-lint` bypass), exec-readable renderer (BLUF, appendix
    divider, zero raw ids above it), run-cycle session-output rule. Read
    `.superpowers/handoffs/output-engineering-DONE.md` for the delivered list + F68 follow-ups
    logged in the backlog.
  - **F52/F53/F54 DONE (branch f52-f53-f54 merged, 5 commits `2a2dae7..2c070f4`; final opus
    review: Ready to merge, no Critical/Important).** F52: docIds vintage-scoped at the gather
    seam (`{slug}-{digest}-{asOf}`; `ingest --as-of` required; finding ids inherit; L1 url+hash
    unchanged). F53: extractor seam rejects measured price rows whose value.unit != the
    registered canonical unit AND `extract --emit-prompt` lists the price-side ids + canonical
    units (F55 pattern; defaults byte-identical). F54: two seed triggers reworded to pass the
    observable heuristic + seed-lint test; live book untouched. New: F56 (tiny, --as-of shape
    validation + two cosmetic minors) added to the backlog.
    **PROCESS CAVEAT:** the user was away at every question gate this session — the spec's
    approach picks (all matching the backlog's stated lean) and the merge decision followed the
    recommended options + prior precedent. Spec flags this in its Decision-provenance note:
    docs/superpowers/specs/2026-07-03-f52-f53-f54-small-fixes-design.md. Relitigate there if any
    pick is wrong.
  - (F52–F54 live verification criteria: see VERIFY NEXT LIVE CYCLES under the approved
    sequence below.)
  - **First MONTHLY live cycle on the sp5 stack** (asOf 2026-07, committed `a8b7398`): scorecard
    `store/chips.merchant-gpu/2026-07-v1.json` DMI +0.633 / SMI −0.453; all 7 standing theses
    judged (3 strengthened→high; custom-asic reaffirmed@high; pricing-power reaffirmed;
    export-control + vendor-financed-circularity weakened→low) + 2 new provisional proposals
    (customer-concentration-risk, networking-attach-as-systems-moat).
  - **F55 DONE (`39f427e`):** emitted prompts now carry the id vocabularies the gates enforce —
    `extract --emit-prompt` lists the taxonomy's valid impact.targets ids; `judge --emit-prompt`
    appends a `<citationGroups>` block (per-dimension id groups + the six DIMENSIONS names);
    thesis SYSTEM states the v1 observable-trigger heuristic verbatim. Default prompt paths
    byte-identical; `tests/test_prompt_vocab.py`. Dispatching sessions no longer supply id lists
    out-of-band — trust the emitted prompt.
- Sub-project 5 (the Thesis Book) is BUILT, MERGED, and LIVE-VERIFIED:
  - **5-1 thesis engine** merged @ `7197226` (11 commits; suite 626→714/3): `gpu_agent/thesis.py`
    (models, rebuild-verified ThesisStore, gate rules 1–7, anti-whipsaw apply engine F5),
    `gpu_agent/memory.py` (F4 bundle), thesis/judge prompts (memory injection, byte-identical when
    absent), `thesis` CLI stage (emit→recorded), run-cycle skill stage (e), seed book
    `registry/theses.chips.merchant-gpu.json`.
  - **5-2 output surgery** merged @ `d5dd492` (6 commits; suite 714→796/3): `gpu_agent/bands.py`
    five-word band map, THE CALLS + WHY renderers in brief.py, page reorder (CALLS → STATE → WHY →
    drill-down → TRUST footer), raw indices demoted to the footer, cli._report book loading, e2e
    acceptance test. One spec-vs-plan conflict resolved under the standing SPEC-WINS rule (WHY
    Contested widened to competitive-lens at any conviction + findingIds on every WHY line).
  - **Integration gate PASSED (2026-07-03 live daily cycle):** THE CALLS renders from a real judged
    book. Store state committed: scorecard `store/chips.merchant-gpu/2026-07-03-v1.json`
    (DMI +0.133 / SMI +0.147), seeded+judged thesis book `store/theses/chips.merchant-gpu/`
    (2 strengthened→high, 3 reaffirmed, 1 weakened→low, +1 provisional proposal), wiki/dedup/L1
    artifacts, finalized `store/cycle-log.json` (every brain re-dispatch reason logged). The F4
    MEMORY block fed both brains live; judged direction moved vs prior (Strong/steady, was
    Strong/improving; bottleneck rotated competitiveStructure→moat).

## IMMEDIATE NEXT TASK — the APPROVED SEQUENCE (user-approved 2026-07-03; full context in
## docs/fix-backlog.md's F57–F66 section header — do not re-derive or re-ask)

Quick wins, independent: **F56** (tiny, --as-of shape validation). F61 is DONE (subsumed by F67).
Then in order — each feature starts with brainstorming, per charter:
0. **F6 second half — MERGED (`87f281a`).** Remaining: Task 10 live baseline only (see
   IMMEDIATE NEXT TASK above) — it arms the hash-pin gate that F57/F58/F62/F63 depend on.
1. **F62** — flagship consumes the daily store (highest-leverage; the monthly brief currently
   discards everything the dailies learned). Interacts with F52 vintage ids + L2 dedup.
2. **F63** — corroboration doctrine (N independent secondary publishers move one bounded step)
   + evidence-sufficiency gate counterweight. Charter Part-37 amendment, migration discipline.
3. **F57/F58/F59** — gather freshness wave (headline/forward slices + per-class doc floors;
   live-mode recency window ~45d; primary allowlist = charter's "filings, official posts").
4. **F60** — let fresh/leading indicators score (registry weights are DATA = safe; any
   scoring.py change ships only as a versioned migration, Part 33).
5. **F64** — trigger-first daily brief + Brier scoring. 6. **F65** — "So what for TSMC"
   section. 7. **F66** — post-hoc citation audit (low priority).
Standing feature track (slot in as capacity allows): F23 compliance matrix, F24 entity
canonicalization, F25 wiki scaling (hard prereq for 34-category fan-out); then WHY-tree,
HTML dashboard, discovery, layer tier, Main roll-up.
REJECTED (user-approved, do not resurrect): SEC-EDGAR/sec-api pipeline; search-API/scraper
benchmarking. Do NOT relitigate sp5 design decisions
(spec `docs/superpowers/specs/2026-07-02-thesis-book-design.md`).
**VERIFY NEXT LIVE CYCLES (F52–F54 criterion #6):** re-gathered URLs mint vintage ids (no
FindingStore collision/exclusions); price rows carry D6/gpuSpotPrice with canonical units;
PMI matches ≥1 series once two post-fix cycles exist; brains echoing seed triggers pass.

## THE BIG DECISIONS ALREADY MADE (do not relitigate without reason)

1. **Output goal:** deterministic, brief-first Market-State brief; pure projection of the store;
   HTML dashboard later. THE CALLS (thesis book, per-cycle deltas) leads the page above STATE &
   WHY; raw indices live ONLY in the trust footer; five-word band map with earned "(was X)".
2. **Lane discipline (Part 21):** merchant-gpu owns merchant vendors only; the cross-cutting
   "GPU market state" brief is a LAYER-TIER product. Category tier does not recommend actions —
   theses are category-scoped falsifiable claims; recommendations stay Layer/Main.
3. **Claude Code IS the brain** — no OAuth/SDK/API. Live extraction/judgment/thesis = TOOL-LESS
   dispatched Opus subagents through `--emit-prompt` → `--recorded`; judgment samples are SEPARATE
   generations (F38); thesis book gets ONE coherent author (no voting); gate rejection →
   re-dispatch the brain with the errors — NEVER hand-edit brain output (held throughout the
   2026-07-03 gate: 5 re-dispatches, all logged in cycle-log.json, zero hand edits).
4. **Price is overlay-only (F8):** D6/gpuSpotPrice never feed DMI/SMI; price-level drafts carry
   polarity 0 (the gate enforces it; non-price findings must move a track).
5. **Contract v1.2 frozen core RE-FROZEN:** `gate.py`, `scoring.py`, `schema/*`,
   `judgment/briefing.py`, `judgment/judge.py` aggregation, `pipeline.py`, `JsonStore`. Sub-project
   5 shipped fully additive (final reviews verified empty frozen diffs on both branches).
6. **Anti-whipsaw lives in code:** secondary-only reversals defer as CHALLENGED; primary evidence
   or a second consecutive signal applies; conviction ±1/cycle; applied broken retires. Promotion:
   provisional → registered at ≥2 cycles + ≥2 publisher domains (F31 key).
7. **Product Q&A decisions** live in `docs/action-items.md`; "nothing changed" is a first-class
   honest headline (renders as the compact book list).

## OPERATING NOTES / INVARIANTS (carry forward)

- Run from repo root `C:\Users\danie\random_for_fun`; Python at `.venv/Scripts/python`
  (recreate: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`).
- Worktrees: `.worktrees/<name>` (gitignored); shared root `.venv` imports the WORKTREE's code when
  pytest runs from the worktree root — no per-worktree venvs.
- Registry/taxonomy paths via `gpu_agent/config.py`; taxonomy lives at `docs/taxonomy.json` and its
  category ids are `<layer>.<category>` (merchant-gpu, hyperscaler-asic, foundry-packaging,
  hbm-memory, …; infrastructure.hyperscale-cloud / infrastructure.neocloud). The six judge
  dimensions: momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk —
  the judge may cite ONLY within each dimension's briefing group (feed the real groups to a
  re-dispatch, never invented names — a 2026-07-03 dispatch error proved the gate catches this).
- The run's `--as-of` overrides the assignment's asOf (F50). Day-grain asOf for daily cycles.
  Tracked-store carve-outs: `store/chips.merchant-gpu/`, `store/wiki/`, `store/findings/`,
  `store/theses/`, `store/seen_docs.jsonl`, `store/cycle-log.json`.
- **Doctrine:** code computes + gates + stores; the brain reasons; nothing un-gated reaches a
  number; every claim cites findings; page text is DATA; every cap/skip/drop logged; provisional
  quarantined; paywalled inventoried + never fetched (TrendForce/SemiAnalysis stayed unfetched
  through the gate); the session NEVER hand-edits brain output — re-dispatch with the errors.
- Tests deterministic; suite green at every merge (**828 passed / 3 skipped** on main). Commit
  trailer names the ACTUAL model. Push freely.
- **Windows:** prefer PowerShell but NOT `>` redirection for UTF-8 (use bash for redirects); avoid
  double quotes inside `git commit -m` (here-strings); synchronous subagent transcripts are NOT
  written to task output files — capture their answers from the tool result (resumed/background
  agents DO write transcripts).
- Model policy: opus for important/final reviews, frozen-adjacent numeric work, and ALL brains;
  sonnet for mechanical per-task implementer/reviewer work.

## WHAT'S DONE (compressed — details in `git log`, the ledger `.superpowers/sdd/progress.md`, docs/superpowers/specs|plans/)

- **sp1–sp4** (harness · live runs · output/coverage · daily monitor) — merged; see ledger.
- **2026-07-02 fix backlog F1–F51:** waves 0/1/2 + contract v1.2 migration + F46 first genuine
  second cycle — all merged + pushed. Suite 417 → 626.
- **Sub-project 5 (Thesis Book):** spec `dd41b5a` → plans `83b7c5b` → 5-1 merged `7197226` →
  5-2 merged `d5dd492` → integration gate passed (this handoff). Suite 626 → 796.
  Ledger has per-task review outcomes + the deferred-minors list for both pieces.
- **F52/F53/F54 small-fix wave:** spec `091c709` → plan `0e6cb0e` → merged (5 commits,
  `2a2dae7..2c070f4`). Suite 804 → 828. Ledger has per-task reviews + the final-review triage.
- **Open user decision:** repo is still named `random_for_fun` — rename before TSMC-branded
  exposure.
