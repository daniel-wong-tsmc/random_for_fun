# HANDOFF — GPU Category Agent (resume point: daily #1 of 2 DONE gate-clean; daily #2 runs tomorrow; blind ablation awaits USER scoring)

- **Date:** 2026-07-05 (evening — post flagship-v3 commit, daily cycle #1, ablation assembly)
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **Desk-LIVE item 1 progress: daily cycle #1 of 2 is DONE and GATE-CLEAN on the current
  stack** (store commit `d9cfb3f`, pushed): scorecard `store/chips.merchant-gpu/2026-07-05-v1.json`
  (DMI 0.040 / SMI −0.027 / SDGI 0.067; Strong/worsening; binding constraint = China
  export-control enforcement, shifted from moat on 3 distinct publishers + a primary SEC
  filing — the F63 sufficiency gate PASSED with **no bypass**; the F71 deadlock did NOT
  recur). Voice lint: 3 judge samples re-dispatched once (CFO/CUDA/ZLUDA/SDNY), passed —
  zero hand edits. Thesis: 12/12 judged first pass; AMD weakened reversal correctly
  DEFERRED by anti-whipsaw (1 publisher < 3); 4 theses promoted to registered; 1 new
  proposal. Run artifacts: `work/daily-2026-07-05/` (gitignored); finalized cycle log
  committed. Known gap logged in the cycle log: the new proposal title carries `CUDA`
  above the fold (F68a thesis-prose lint wiring is still deferred). Eval pin verified
  GREEN after the run (no prompts touched).
  **NEXT: daily cycle #2 (gate-clean, day-grain asOf 2026-07-06) — that plus the 2026-07
  flagship clears desk-LIVE item 1.**
- **The 2026-07-05 flagship v3 store state is now COMMITTED** (`99ca522`) — the prior
  session had left it uncommitted in the working tree. Its cycle log (with the F71
  `sufficiency: bypassed` record) is preserved in that commit's `store/cycle-log.json`.
- **Blind baseline ablation ASSEMBLED — awaiting USER scoring** (`639c00d`, pushed):
  `docs/ablation-2026-07/{A,B,C}.md` = the desk render vs an RSS-digest baseline vs a
  one-shot deep-research baseline (both web-only, zero repo context; citations verified
  web-only), randomly assigned; mapping ONLY in `ANSWER-KEY.md`. **The user scores
  `SCORING.md` before opening `ANSWER-KEY.md`** — do not reveal or consult the mapping in
  session output; record the verdict in `docs/action-items.md` once scored.
- F71 (anchor-bound vs sufficiency-gate precedence) remains OPEN in the backlog — it did
  not fire this cycle but must land before any unattended loop runs a cycle.

## HISTORICAL — F63 state at merge time (2026-07-05, superseded by the section above)

- Main was green and pushed at `9292751` (includes the eval-v2 merge `c0d5dd2`; suite on
  merged main 1031/4). The F63 branch passed its v2 gate (`ef52790`): extract 6.625 /
  judge 7.75 / thesis 6.00 vs bars 6.5833/7.3333/5.6667, no craters; rebaselined via the
  `--verdict` governance path (no force); suite on the branch 1059/4/0. F63 then MERGED
  to main `017b592`. Run journal:
  `docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md`; raw runs (gitignored):
  `work/eval-f63-regate-2026-07-05/{r1,r2,r3}` plus the 2026-07-04 runs — never `git clean`.

## HISTORICAL — F63 pre-eval-v2 state (superseded 2026-07-05 by the section above)

- **Tasks 1–7 complete, reviewed, committed** on branch `f63-corroboration-doctrine`
  (worktree `.worktrees/f63-corroboration` — do NOT `git clean` it; gitignored `work/` holds
  both eval runs' raw data). Ledger: worktree `.superpowers/sdd/progress.md`.
  Built: `gpu_agent/publisher.py` (F31 identity, single source of truth); `registry/corroboration.json`
  (`minDistinctPublishers: 3`) + `config.min_distinct_publishers()`; the ONE sanctioned frozen-core
  edit — `gate.py` F2e secondary-corroboration exception (contract v1.2→v1.3, migration note in
  `docs/migrations/2026-07-contract-v1.3.md`); `thesis.py` anti-whipsaw rule-6 corroborated-step
  (`corroboratedStep` recorded, logged, no auto-resolve); `gpu_agent/sufficiency.py` +
  evidence-sufficiency gate wired at `judge --recorded` / `pipeline --recorded-judge`
  (`--no-sufficiency` bypass); three amended SYSTEM prompts (extract corroboration exception,
  thesis ≥3-publisher reversal exception, judge sufficiency rule); charter Part 37 amendment.
- **Task 8 (run-eval) ran TWICE and FAILED TWICE** vs the F62 incumbents (extract 6.75 /
  judge 7.50 / thesis 6.00): attempt 1 = 6.38/7.00/6.00-tie; full replication = 6.38/6.75/5.50.
  Pre-committed disposition executed: STOP, pin stays red, NO rebaseline, NO --force.
  **Diagnosis (evidence in the run notes): the deficits are incumbent-bar noise, not F63
  regressions** — the bar is F62's high-draw attempt 3; identical-prompt runs swing 6.25–7.50;
  no deduction in either run traces to the F63 prompt changes, and the F63 mechanisms graded
  WELL (F2e caught the within-document-corroboration error in BOTH runs' fresh generations;
  a judge visibly kept the prior binding constraint citing single-outlet evidence).
  Durable notes (committed): `docs/superpowers/eval-notes/2026-07-04-f63-run-notes.md`.
  Raw runs (gitignored): worktree `work/eval-f63-2026-07-04/` and `-r2/`.
- **RECOMMENDATION MADE TO USER (2026-07-05), NOT YET APPROVED — do not start without a user go:**
  build **eval-v2** as its own feature (brainstorm → spec → plan → SDD, branch from main):
  (1) baseline = N=3 replicate runs storing per-seam mean + per-run scores + per-case medians;
  (2) gate = one fresh run vs baseline-mean − ε (ε computed from the stored replicates,
  deterministic); marginal fail auto-triggers exactly ONE replication, two-run mean decides,
  hard stop; (3) add a per-case crater prong (fail if any case drops ≥3 vs its baseline median);
  (4) frozen negatives unchanged. Then re-gate F63 under the new rule (no judgment-call pass).
  Optional fold-in to F63 before its re-gate (user to confirm): the two proven prompt
  clarifications — corroboration counts publishers "across separately fetched documents",
  and state the `impact.direction` enum — plus the `CEO` acronyms.json allowlist entry.
  User's alternatives if they reject eval-v2: A force-rebaseline / B more replications / D hold.
- **F63 merge blockers (in order):** user decision on eval-v2 → gate PASS → final whole-branch
  review (opus, review-package from merge-base; not yet run) → rebase/merge onto current main
  (main advanced past F63's base — careful with shared frozen files) → USER GO to merge.
- Fix-backlog additions from the runs are in `docs/fix-backlog.md` ("F63 eval-run findings").

## ⚠ 2026-07-05: EVAL-V2 MERGED (`c0d5dd2`) — the eval gate rule CHANGED

- `fixtures/evals/baseline.json` is now **schema v2**: 3 replicate runs; bar = replicate mean − ε
  (extract ≥ 6.5833 / judge ≥ 7.3333 / thesis ≥ 5.6667) + per-case crater prong (median − 3);
  marginal fail ⇒ exactly ONE replication, two-run mean decides. `eval rebaseline` now takes
  `--runs <d1> <d2> <d3>` (+ `--verdict` governance proof); the old `--out` form is GONE.
  Follow the rewritten `.claude/skills/run-eval/SKILL.md`. Spec:
  `docs/superpowers/specs/2026-07-05-eval-v2-replicate-baseline-design.md`. Suite on merged
  main: 1031 passed / 4 skipped. (This instance works `.worktrees/eval-v2` + the F63 re-gate;
  the authoritative full HANDOFF still lives on the f63-corroboration-doctrine branch.)

## ⚠ CONCURRENT-INSTANCE COORDINATION (still live)

- **F74 (cycle-log clobber fix) CLAIMED 2026-07-05 ~21:30 +0800** — worktree
  `.worktrees/f74-cycle-log`, branch `f74-cycle-log` off `29584d9`. Scope: guard in
  `cli._cycle_plan` (refuse to overwrite an enriched journal), run-cycle SKILL.md step 1
  plan-path change (plan → run's `work/` dir), journal tripwire test. Claimed files:
  `gpu_agent/cli.py` (_cycle_plan only), `.claude/skills/run-cycle/SKILL.md`,
  `tests/test_cli_cycle_plan.py` + one new test file, `docs/fix-backlog.md` (F74 entry).
  **Root `store/cycle-log.json` is NOT claimed** — it currently belongs to the in-flight
  2026-07-05 daily run; its restore (F74 step 1) waits until that run finalizes + commits.
  To the daily instance: your journal finalize step is unaffected; do NOT commit the bare
  cycle-plan skeleton — enrich or restore from `99ca522` first.

- F67 is DONE (merged `b0e8061`, completion handoff `.superpowers/handoffs/output-engineering-DONE.md`).
- **F69 (web-reach layer) is DONE — merged to main `e167c6b` (2026-07-04); branch
  `f69-web-reach-layer` deleted.** Data-driven registry `registry/web-reach-tools.json`
  (agent-reach first; a 2nd github drops in as a data entry), health-check preamble +
  gatherer-contract additions in `gather-category`, doctrine in charter Part 37, operator doc
  `docs/web-reach.md`. Frozen core untouched; no scoring change (corroboration math stays F63 —
  see the F63 handoff note in the backlog). Spec/plan 28e38de/a23467f; final whole-branch review
  clean. (Earlier cross-branch mixup with this instance — a stray commit onto the F69 branch —
  was resolved before the merge.)
- **F70 (last30days — 2nd web-reach github) is DONE — merged to main `7938eb4` (2026-07-04);
  branch `f70-last30days-webreach` deleted.** Adds `mvanhorn/last30days-skill` to
  `registry/web-reach-tools.json` as tool #2 and introduces a `role` field: `fetch` (agent-reach —
  raw content → secondary blobs) vs `discovery` (last30days — a last-30-days multi-platform
  synthesizer used for **leads only**: mined for leads in gather Round-building step 2b, its
  synthesized brief NEVER ingested as a blob — Part 37). Role-aware step-3 gatherer contract +
  charter Part 37 `role` clause + `docs/web-reach.md`. Whole-branch review caught + fixed a Critical
  (the subagent contract was not role-aware). Frozen core untouched.
- **NOTE — `docs/roadmap.md`:** the concurrent instance committed its 326-line roadmap doc to main
  as **`c4913a6`** (independent of F69/F70), landed on top of `ed378ae` while F70 was on its branch.
  main had advanced to `c4913a6` before the F70 merge, so it rode into origin via the F70
  merge/push — it is the concurrent instance's own commit, not part of F70. (My F70 charter commit
  had briefly swept an earlier untracked copy in via `git add -A`; that was un-bundled, so F70's own
  commits contain only F70 files.)

## STANDING RULE (F6 gate, now ACTIVE)

Any edit that changes the emitted brain prompts (extraction/judgment/thesis prompt files, their
cli vocab glue, or registry vocab data) turns the suite RED via
`tests/test_evals_baseline_pin.py`. The unlock is NEVER a hand-edit of `fixtures/evals/baseline.json`:
run `.claude/skills/run-eval/SKILL.md` (re-dispatch brains + graders), then
`gpu-agent eval rebaseline`, and commit the new baseline WITH the prompt change. F57/F58/F62/F63
prompt work all flows through this gate.

## IMMEDIATE NEXT TASK — await user decision on eval-v2, then either build it or execute the chosen F63 disposition

Sequence position: F62 ✅ MERGED (`eb925bc`) → **F63 BUILT/BLOCKED (see top section)** →
F57/F58/F59 → F60 → F64 → F65 → F66. Eval-v2, if approved, slots in as its own feature before
F63's re-gate. F56 remains a safe tiny side item.

## Newest state (newest first)
  - **`docs/roadmap.md` — the phased roadmap from this one desk to the full charter product
    (2026-07-04): forks user-approved live (layer tier after cats #2–3, Main after ~2 layers,
    coarse size tags); final doc committed under the AFK precedent — open questions inside.**
  - **F6 TASK 10 DONE — initial eval baseline committed (`0344949`), hash-pin gate ARMED.**
    Live run 2026-07-04 (all tool-less Opus): 14 fresh brains + 1 F38-safe voice re-dispatch, all
    gate-clean; 18 rubric graders + 1 schema re-dispatch. Seam means extract 6.62 / judge 6.75 /
    thesis 5.50; calibration held (negatives 2/1/0/2 of 8, limit 4). The run itself caught and
    shipped three fixes (eval working as designed on day one): extract prompt was missing the
    demand/supply indicator vocabulary — context-free brains were 100% gate-dropped (completes
    F55; `6d9fa67`+`f1dc904`); F67 voice-lint acronym allowlist gaps (GB300/GAAP/GDP) + an
    abbreviation-blind sentence splitter that counted "U.S." as a sentence end (`ac1e209`); one
    golden-case gate-outcome re-pin (`4aa8154`). Run artifacts: `work/eval-2026-07-04/`
    (RUN-NOTES.md is the full run journal).
  - **F6 SECOND HALF MERGED (`87f281a`, user-approved; 15 branch commits; suite 910/5 verified
    on merged main and pushed).**
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
- **F62 (flagship consumes the daily store):** spec `de0719b` → plan `d18c0c2` → implemented on
  branch `f62-flagship-consumes-store` → **MERGED to main `eb925bc` (2026-07-04, user go);
  suite on merged main 974 passed / 3 skipped** (F62 + F70 combined).
  New `gpu_agent/corpus.py` (45-day windowed store↔fresh union), `corpus` CLI,
  `pipeline --corpus-store/--corpus-report`, `observed=` vintage tag (emit-only kwarg),
  judge crux sentence now demands a consensus-departure (`b8f41f8`), run-cycle wiring +
  write-back. Frozen core empty-diff vs main; final opus whole-branch review APPROVED
  (0 critical/important, all minors ride). **Eval RESOLVED on merit after three attempts:**
  attempts 1-2 failed the judge seam (6.50, 6.25 vs incumbent 6.75) with one signature — all 8
  generations missed the rubric's consensus-departure point the 3-sentence voice budget never
  asked for; user chose option B (fix the prompt, keep the rubric); attempt 3 PASSED
  (extract 6.75 / judge 7.50 / thesis 6.00 — sensitivity-differentiation went 1→2 on all four
  judges) and the baseline was rebaselined WITHOUT --force (`f605a77`). Suite on the branch:
  **970 passed / 3 skipped / 0 failed.** Full three-attempt history in
  `docs/superpowers/2026-07-04-f62-eval-run-notes.md`; raw runs in the worktree's gitignored
  `work/eval-f62-2026-07-04/` (attempts 1-3 preserved — do not `git clean` that worktree).
  Ledger: `.superpowers/sdd/f62/progress.md` (repo root).
- **Open user decision:** repo is still named `random_for_fun` — rename before TSMC-branded
  exposure.
