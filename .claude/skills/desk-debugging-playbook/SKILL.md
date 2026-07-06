---
name: desk-debugging-playbook
description: Use when a GPU Category Agent run, eval, or test fails or looks wrong in this repo — stderr shows 'DROPPED', 'voice-lint:', 'sufficiency:', 'GATE FAILED', 'REGISTRY GATE FAILED', or 'DROPPED-KNOWN'; exit 2 'recorded answers (N) != documents/samples'; LLMError 'no recorded response for this call' or 'no valid output after 3 attempts'; a TypeError replaying a recorded answer; tests/test_evals_baseline_pin.py red; grader answers rejected for extra keys; PMI renders '—'; store/cycle-log.json looks skeletal; a category's scorecards missing from git status; wiki updates split across nvda/nvidia pages; UnicodeEncodeError (charmap/cp1252), NativeCommandError on git, or python3 opening the Microsoft Store on Windows.
---

# Desk Debugging Playbook

## Overview

This pipeline fails loud and deterministically: nearly every symptom maps to one specific gate,
seam, or environment trap, and the stderr prefix names the gate. Match the symptom below and run
the discriminating check BEFORE changing anything — the most expensive mistakes here were fixes
applied to the wrong layer.

**Standing law (maintainer-confirmed):** a rejected brain answer is a re-dispatch instruction,
never an edit target. Append the verbatim violation lines to the same emitted prompt and
re-dispatch only the violator. Never hand-edit brain outputs, recorded answers, or
`fixtures/evals/baseline.json`. Fix forward, never revert.

## When to use

- Any non-zero exit, traceback, or rejected answer from `gpu_agent.cli` verbs, live or recorded.
- Red tests after an edit, especially `tests/test_evals_baseline_pin.py`.
- Output looks wrong without an error: missing dimension, wrong prior/delta, PMI `—`,
  vanished artifacts, wrong wiki page.
- Windows-flavored weirdness during desk work (encoding crashes, phantom diffs, stub python).

## When NOT to use

| Question | Go to |
|---|---|
| WHY is the system designed this way / is this behavior intentional? | desk-architecture-contract |
| How do I run/rerun a cycle, gather, or dispatch subagents? | desk-run-and-operate (routes to run-cycle / gather-category) |
| Eval mechanics: replicates, verdicts, rebaseline, fixture families | desk-validation-and-qa; execution via the repo run-eval skill |
| I need to CHANGE something gated (gate.py, prompts, .gitignore, registry semantics) | desk-change-control |
| Full history of an investigation / was this tried before? | desk-failure-archaeology |
| Measure store/wiki/dedup state instead of eyeballing | desk-diagnostics-and-tooling |
| Fixing F74/F71/F75/F72 themselves | gate-integrity-campaign |
| What a rating/dimension/Finding SHOULD mean | market-state-reference |

## Step 0: read the failure shape

| Signal | Meaning |
|---|---|
| exit 2 | Operator error: wrong answer count, missing/malformed args. Fix your inputs, nothing was gated. |
| exit 1 + prefixed stderr lines | A gate fired. The prefix names it (table below). |
| Raw Python traceback | Answer-shape problem or a masked judgment conflict (`LLMError`/`JudgmentError`/`TypeError` are NOT caught by the CLI on judge/pipeline paths). |
| exit 0 but output looks wrong | Semantic issue — see "Silent and look-wrong symptoms". |

| stderr prefix | Gate | Emitted by |
|---|---|---|
| `DROPPED <id>: ` | Extraction seam + finding gate | extract / pipeline / eval record-brain |
| `voice-lint: sample <n>: ` | F67 analyst-voice lint | judge --recorded, pipeline --recorded-judge |
| `sufficiency: sample <n>: ` | F63 evidence-sufficiency gate | judge --recorded, pipeline --recorded-judge |
| `GATE FAILED:` | Scorecard gate (fixture run/score paths only) | run / score |
| `REGISTRY GATE FAILED:` | Registry load/resolve failure | corpus / judge / thesis / eval / pipeline |
| `CYCLE SCOPE ERROR:` | Bad --scope | cycle-plan |
| `SKIPPED <cat>: skipped-no-assignment` | No assignment file — expected for 32/34 categories, not an error | cycle-plan |
| `DROPPED-KNOWN <url>: ` | L1 seen-doc dedup (only with --dedup-store) | ingest |

The complete enumerated catalog of every rejection string, with file:line sources and F-items,
is in [references/rejection-strings.md](references/rejection-strings.md).

## Master triage table

### A. Recorded-answer shape errors (the #1 failure mode)

The three answer shapes are frozen: **extract** = JSON array of serialized-object STRINGS, one
per document, in the emitted doc order (`["{...}", "{...}"]`, like
`fixtures/recorded/extract-nvda.json`); **judge** = array of exactly `--samples` (default 3)
serialized JudgmentResult strings; **thesis** = ONE JSON object, not an array, not a string.

| Symptom (exact where possible) | Likely cause | Discriminating check | Fix / route |
|---|---|---|---|
| exit 2 `recorded answers (N) != documents (M)` | Extract answer has wrong element count — subagent merged/split docs | Count elements vs files in `--docs` dir | Re-dispatch the brain quoting the array-of-strings contract; never pad or trim the array by hand |
| exit 2 `recorded answers (N) != samples (M)` | Judge answer array length ≠ `--samples` | `python -c "import json;print(len(json.load(open('judge-answer.json'))))"` | Re-dispatch missing sample(s) as separate subagents; or pass the matching `--samples` if you deliberately ran fewer |
| `TypeError: the JSON object must be str, bytes or bytearray, not dict` traceback | Array elements are raw OBJECTS, not serialized strings | Open the file: elements start `{` unquoted | Re-serialize is tempting but forbidden if it alters content — re-dispatch with the shape contract quoted. (Pure transport normalization — e.g. saving the final complete JSON object from a self-correcting reply — is the ONE allowed transformation; log it in run notes.) |
| `LLMError: no valid output after 3 attempts: <JSONDecodeError>` | Markdown code fences or trailing prose — NO fence-stripping exists anywhere in gpu_agent; recorded mode re-serves the same answer on retry (F11) | First chars of the answer string are ` ``` ` | Re-dispatch with "Return ONLY JSON, no prose, no code fences" + the error; fence-stripping to salvage is transport normalization — allowed, but log it |
| `LLMError: no valid output after 3 attempts: <ValidationError ... extra_forbidden>` | Brain/grader added extra keys (drafts forbid `side`, `tier`, `id`; graders emit stray `score_note`/`verdict`) | Read the pydantic error field names | Shape-only re-dispatch: "keep your content; remove the extra keys." Extra keys at the TOP level of ExtractionResult pass (only per-draft models forbid extras) |
| `LLMError: no recorded response for this call` (traceback) | The judge answers had an anchor/citation conflict; the resample loop retried and starved the RecordedClient. The REAL conflicts are never printed | Run `scripts/judge_conflicts.py` (this skill) — replays with resample_budget=0 and prints the actual JudgmentError list | Re-dispatch the conflicting sample(s) with the printed conflicts appended (F38 protocol) |

### B. Gate rejections (exit 1, prefixed lines)

| Symptom | Likely cause | Discriminating check | Fix / route |
|---|---|---|---|
| `DROPPED <id>: unregistered indicator: <x>` | Brain invented an indicator id | Is `<x>` in `registry/indicators.json`? Vocab has been IN the emitted prompt since F55 — if this fires live, the brain ignored it | Re-dispatch that doc's prompt with the violation appended. Do NOT add the indicator to the registry to make it pass (registry additions route via desk-change-control) |
| `DROPPED <id>: excerpt not found in source document` | Paraphrased "quote" (check is whitespace-folded but case-sensitive) | Diff the excerpt against the snapshot in `work/docs/<docId>.json` | Re-dispatch demanding verbatim excerpts |
| `DROPPED <id>: price unit '<u>' != registered unit ...` | F53: unit drift OR the wrong price indicator (D6 vs gpuSpotPrice) | Compare against the unit in the prompt's price-vocab block | Re-dispatch; if genuinely a new unit/series, that is registry work — desk-change-control |
| `DROPPED <id>: secondary-only evidence cannot support high confidence (k < 3)` | F2e working as designed | Count distinct netlocs in the finding's evidence | Usually correct behavior: brain should have said medium. Re-dispatch. If 3+ REAL distinct publishers exist as separate docs, they merge at L2 dedup — check the corroborators were each fetched as their own blob |
| `voice-lint: sample <n>: <field>: <k> sentences (max <m>)` but you count fewer | Regex splitter false positive: only U.S./U.K./e.g./i.e./vs. are protected abbreviations; "Corp. The", "No. 4" etc. split | `.venv/Scripts/python -c "from gpu_agent.reader import split_sentences; print(split_sentences('<text>'))"` | Re-dispatch asking to rephrase around the abbreviation. Extending the lookbehind list is a code fix (lane-shaped, cite F67 precedent at reader.py:34-39) — desk-change-control |
| `voice-lint: ... acronym '<A>' not on registry/acronyms.json allowlist` | Legit domain acronym echoed from findings (precedents: CEO, GB300, GAAP, GDP), or actual jargon | Is it a real market/finance acronym an exec reads daily? | Either extend the DATA file `registry/acronyms.json` (never weaken `lint_prose`), or re-dispatch to rephrase. One rewrite attempt, then logged bypass per run-cycle |
| `sufficiency: sample <n>: <dim>: rating changed X->Y with insufficient evidence` | F63 gate doing its job — the change lacks primary or 3-publisher backing | Was there a real state change or is the brain drifting? Check prior scorecard's rating | Re-dispatch: "keep every rating you can justify; for the flagged changes, either cite findings meeting the bar or keep the prior rating." Second failure → logged `--no-sufficiency` bypass per run-cycle — but note F75 targets this; record the bypass in the cycle log and run-health lines |
| voice-lint AND anchor-bound demands contradict (rating forced up, sufficiency objects) | F71 deadlock (OPEN) — two gates with no coded precedence; happened live 2026-07-05 (d0b39ea) | Does the flagged dimension's anchor force the move? Check anchors.json / the emitted briefing | STOP and escalate to the user unless mid-run: the run-cycle interim is one rewrite then logged bypass. The real fix is gate-integrity-campaign's F71 |
| `GATE FAILED:` / GateError traceback from pipeline | Scorecard-level violation (unknown finding cited, anchor contradiction, dashboard self-reference) | Read the dimension-prefixed lines | If from a recorded judge answer: re-dispatch. If from YOUR fixture edits: fix the fixture inputs, never gate.py |
| Thesis rejection lines (`missing falsifiableTrigger`, `trigger names no observable`, …) | Thesis answer below the depth bar | — | Re-dispatch up to 2 attempts, then mark `thesis: failed` in the cycle log; a thesis failure NEVER blocks the scorecard; the book is untouched on rejection |

### C. Eval-adjacent symptoms

| Symptom | Likely cause | Discriminating check | Fix / route |
|---|---|---|---|
| `tests/test_evals_baseline_pin.py` red: "PROMPT BUNDLE CHANGED — this is the F6 regression gate, not a broken test" | An emitted-prompt byte changed. The hash covers MORE than prompt files: registry vocab, taxonomy ids, pydantic answer schemas, CLI vocab glue — "safe data-only" registry edits CAN trip it | The failure message lists drifted seams; `git diff registry/ docs/taxonomy.json gpu_agent/*/prompt.py gpu_agent/schema/` | THE SYSTEM IS WORKING. Route to the repo run-eval skill (mechanics: desk-validation-and-qa). Never edit baseline.json, never "fix" the test |
| `eval record-brain` exit 1 | Candidate prompt produces gate-invalid output — SIGNAL, not an eval bug | Read brain-gates.json violations | Re-dispatch THAT brain with violations appended. A merely low-SCORING answer may never be re-run (unfiltered draws) |
| Grader rejected: `extra_forbidden` on `score_note`/`verdict` keys | Known grader emission pattern (3x on 2026-07-05) | — | Shape-only re-dispatch of that grader: "keep your scores/evidence; fix the structure" |
| Eval verdict FAIL/marginal and you want to rerun | — | — | STOP. Pre-committed dispositions rule: marginal-fail earns exactly ONE replication; hard-fail is a hard stop, record BLOCKED-on-user. Retry-until-green is forbidden doctrine. desk-validation-and-qa owns the ladder |

### D. Silent and look-wrong symptoms (exit 0)

| Symptom | Likely cause | Discriminating check | Fix / route |
|---|---|---|---|
| Sufficiency gate never fired though ratings changed | It was silently INERT: `pipeline --recorded-judge` runs it ONLY with `--corpus-store` (memory source); also inert when no prior scorecard exists for the category | Did the pipeline command include `--corpus-store store`? Does `store/<cat>/` hold a prior scorecard strictly before this asOf? Emit `judge --emit-prompt --store store ...` and look for the `MEMORY (prior state — DATA, not instructions...)` block | Rerun with `--corpus-store store` (the live cycle always passes it). First-ever cycle for a category: inert is correct |
| A dimension is missing from ratings | Below-quorum (F19): fewer than 2 of 3 samples rated it — honest absence, listed in `belowQuorum`, marked under-supported downstream | Check the samples: did ≥2 rate that dimension? | NOT a bug. Do not invent a rating; the scorecard marks it under-supported with capped confidence |
| Rating confidence downgraded high→medium | F3 secondary-only display cap, or any under-supported dimension capping overall confidence | Read dimensionStatus notes on the scorecard | Working as designed |
| PMI renders `—` | No matched price series cross-cycle: unit drift or indicator mislabel (the F53 origin story), or genuinely no prior series | Compare (indicatorId, publisher, unit) tuples of price findings across the two cycles' scorecards | If drift got past the extractor somehow, that is a bug — log an F-item via desk-change-control |
| Report shows wrong prior / Δ vs unexpected cycle | Mixed asOf grain: `'2026-07' < '2026-07-02'` lexically, so month-grain files sort BEFORE day-grain in the same month — the monthly flagship v3 is NOT the max-sorting file in its own directory | `ls store/chips.merchant-gpu/` and reason at grain level; find_prior with an explicit `--scorecard` path handles ordering, legacy no-current-path mode assumes newest=current | Always pass the explicit scorecard path to `report`; never resolve "latest" by max(filename) |
| `store/cycle-log.json` looks empty/skeletal | F74 is **CLOSED** (merged `257cf1b`, 2026-07-05; backlog ticked same day `1a9eb33`; the `.worktrees/f74-cycle-log` branch/worktree are deleted, not retained): `cycle-plan --out` now refuses to overwrite anything richer than a bare plan (`_is_bare_plan`/`_cycle_plan` in cli.py, ~lines 813-848, naming F74 in its own error). A skeleton found TODAY means either a pre-fix branch/worktree, or something hand-writing/bypassing `cycle-plan` — not the old unconditional-overwrite trap, which this history once was: it destroyed the F71 bypass record once (survives at commit 99ca522) before the fix | **FIRST MOVE, always: `git diff store/cycle-log.json`.** Fewer keys for the same scope+asOf = clobber; a different scope/asOf = legitimate slot reuse (the file is single-run state, git history is the archive) | Never blanket `git add store/` (the guard is pytest/write-time only — a stale staged blob still slips through). If clobbered: `git restore store/cycle-log.json` only after confirming no live instance owns the change, then re-apply your run's entries. Standing monitor: desk-diagnostics-and-tooling's `f74_guard.py` |
| Second category's scorecards absent from `git status` after a run | `.gitignore` whitelist is category-hardcoded: `store/*` ignored with `!store/chips.merchant-gpu/` — `models.frontier-closed` has NO carve-out (runnable-per-pins, never yet run live) | `git check-ignore -v store/models.frontier-closed/<file>.json` | Add the negation line BEFORE committing the run ("a cycle that isn't committed didn't happen"). Gitignore axes: desk-config-and-flags; the change itself: desk-change-control |
| Wiki updates land on the wrong entity page / one company split across pages | F24 (OPEN): no entity canonicalization — `entity:nvda`, `entity:nvidia`, AND a degenerate `entity:multi` coexist in store/wiki/entity/ today | `ls store/wiki/entity/`; grep `store/wiki/log.jsonl` for the finding's entity string | Do NOT hand-merge pages. Routing keys off the finding's `entity` field verbatim; keep entity strings consistent at gather time. F24 fix: feature track via desk-change-control |
| Extract emits 0 findings, everything dropped | Doc content empty/mangled at ingest, or brain ignored the vocab | Read `work/docs/<docId>.json` content field; read each DROPPED reason | Reasons are per-draft and specific — triage each via section B |
| `judge --recorded` used for the scorecard and memory/lint behaves oddly | Wrong verb: production judging is `pipeline --recorded-judge`; `judge --recorded` is the standalone path with `--store` (not `--corpus-store`) as memory source | Which command did the run script use? | Follow run-cycle step (d) verbatim — desk-run-and-operate |

### E. Windows-layer symptoms (keep short — environment setup lives in desk-build-and-env)

| Symptom | Cause | Check | Fix |
|---|---|---|---|
| `NativeCommandError` on a git command that clearly succeeded | PowerShell 5.1 wraps native stderr in ErrorRecords when redirected; git writes progress to stderr | `$LASTEXITCODE` is 0 | Don't redirect stderr of native exes in PS 5.1; trust exit codes, not `$?` |
| `UnicodeEncodeError: 'charmap' codec can't encode character` | cp1252 console vs report glyphs (↑↓→—Δ). The `report` verb self-reconfigures stdout to UTF-8 (cli.py:911-912) but OTHER verbs and subprocess captures don't | Does it reproduce with `$env:PYTHONIOENCODING='utf-8'`? | Set `PYTHONIOENCODING=utf-8` for captures; in Git Bash: `PYTHONIOENCODING=utf-8 .venv/Scripts/python ...` |
| `python3` opens Microsoft Store or exits silently | `python3` resolves to the WindowsApps alias stub (verified: `C:\Users\...\WindowsApps\python3.exe`) | `where.exe python3` | Always `.venv/Scripts/python` from repo root; from a worktree `../../.venv/Scripts/python` |
| Whole files show as modified with no visible change | CRLF: `core.autocrlf=true`, no `.gitattributes` in this repo | `git diff --ignore-cr-at-eol` empty? | It's line-ending noise — don't commit it; CRLF-vs-LF between materialized eval prompt files is NOT a real change (eval-driver precedent) |
| `FileNotFoundError: registry/acronyms.json` (or indicators.json) | CWD is not repo root — reader.py and config paths are CWD-relative and env-blind (reader ignores GPU_AGENT_REGISTRY) | `pwd` | Run CLI verbs from repo root (or worktree root when testing worktree code) |

## Discriminating experiments (cheap, read-only)

1. **Masked judge conflict vs missing answer:**
   `.venv/Scripts/python .claude/skills/desk-debugging-playbook/scripts/judge_conflicts.py <findings.json> <judge-answer.json> <categoryId>`
   — prints the real JudgmentError list that `no recorded response for this call` hides. Exit 0 = clean, 1 = conflicts/shape.
2. **Gate vs shape:** exit 2 → your inputs; exit 1 + prefix → gate; traceback → shape/conflict.
3. **Sufficiency armed or inert:** `judge --emit-prompt --findings <f> --category <id> --store store | grep -c "MEMORY (prior state"` — 0 means no memory, gate inert.
4. **Splitter or prose:** `.venv/Scripts/python -c "from gpu_agent.reader import split_sentences; print(split_sentences('''<text>'''))"` — count the real segments.
5. **Tracked or ignored:** `git check-ignore -v <path>` names the exact .gitignore line.
6. **Clobber or legitimate slot reuse:** `git diff store/cycle-log.json` — same scope+asOf with fewer keys = clobber.
7. **Pin red from your edit or a data edit:** the assert message lists drifted seams; `git diff --stat registry/ docs/taxonomy.json gpu_agent/` narrows the culprit.
8. **L1 drop legitimacy:** `grep "<sha or url>" store/seen_docs.jsonl` — remember the key is CONTENT HASH first (F12); a known URL with new content is never dropped.
9. **F-item really open?** Checkboxes in docs/fix-backlog.md are stale for several merged items — `git log --oneline --grep="F<nn>"` is the truth (status doctrine: desk-docs-and-writing).
10. **Windows or pipeline:** rerun the exact command with `PYTHONIOENCODING=utf-8` and from repo root; if it passes, it was the environment, not the pipeline.
11. **Anchor arithmetic by hand:** anchor per dimension = mean over its findings of polarity-on-track × magnitude / 3; bound: Strong/Very strong need anchor > −0.15, Weak/Very weak need < 0.15, Mixed always legal. Recompute from the findings file before suspecting the gate.

## Traps that cost real time (one line each, with the receipt)

- **F55**: sessions hand-fed indicator vocab out-of-band; a context-free brain invented ids and the gate dropped 11/11 drafts — one full re-dispatch wave per cycle until vocab was baked into emitted prompts.
- **F53**: 07-02 labeled marketplace prices D6, 07-03 labeled them gpuSpotPrice — both registered, zero matched series, PMI `—`; fixed by canonical-unit rejection at the extractor.
- **F38**: all 3 judgment samples once came from ONE subagent — correlated votes, fake self-consistency, undetectable downstream; samples are now N SEPARATE dispatches, always.
- **F11**: recorded retry used to consume the NEXT doc's answer, cross-attributing findings between documents; now the same answer is re-served and fails loud.
- **F36**: anchor tolerance was ±0.5 — "Very strong" at anchor −0.49 passed; tightened to ±0.15 in contract v1.2.
- **F71** (open): anchor bound forced moat Weak→Mixed, sufficiency correctly objected (2 publishers < 3) — the first live firing of the gate ended in the whole-run bypass the spec forbade (d0b39ea).
- **F74** (closed 2026-07-05, merged `257cf1b`): the cycle-plan step used to clobber the session-authored run journal, erasing the F71 bypass record — it survived only at commit 99ca522; the guard is now live in `cli.py`, but the `git diff store/cycle-log.json` reflex is still worth keeping (the guard is pytest/write-time only).
- **"U.S. GDP" sentence split** (F6 eval day one): the splitter counted "U.S." as a sentence end and tripped the max-2 lint; fixed with fixed-width lookbehinds (reader.py:34-39) — the pattern generalizes to any unprotected abbreviation.
- **F52**: re-gathered URLs minted the same finding ids as the prior cycle; FindingStore failed loud on id collision — doc ids are vintage-scoped now.
- **F62 eval attempt 2**: all 8 judge generations failed the same rubric point the prompt never asked for — a systematic prompt deficit reads as a consistent grade signature, not noise (full saga: desk-failure-archaeology).
- **F69 mixup**: a concurrent instance's stray commit landed on another lane's branch — hence `git log --oneline -1` immediately before every commit.
- **agent-reach doctor exits 120** by design; health truth is `agent-reach --version` (commit 2fee7b5) — do not declare the tool broken from `doctor`.

## Common mistakes

- **Hand-editing anything a gate rejected** — brain answers, recorded files, baseline.json. The only unlock is re-dispatch (with verbatim violations) or, for the pin, the run-eval flow. Maintainer-confirmed law with 5+ documented precedents of doing it right under pressure.
- **"Fixing" the failing pin test or gate code to make a symptom disappear.** gate.py, scoring.py, the Finding schema, the six dimensions, and the rating scale are frozen — changes are Part-33 migrations via desk-change-control, full stop.
- **Switching `--backend anthropic_api` to cure `LLMError` from the default backend.** The raise IS the design (session-driven brain); the SDK backend exists in code but is doctrine-forbidden on the live path.
- **Blanket `git add store/`** — the F74 clobber becomes permanent history. Stage store files surgically after diffing each.
- **Re-dispatch loops:** voice-lint and sufficiency each get exactly ONE rewrite attempt, then a logged bypass; general gate rejections get one or two re-dispatches, then the category is marked failed. Eval replicates are unfiltered draws — a low replicate is never re-run.
- **Treating a missing dimension, `SKIPPED ... skipped-no-assignment`, under-supported notes, or a top-up replicate's printed MARGINAL-FAIL as errors** — all are honest designed states.
- **Trusting docs/fix-backlog.md checkboxes or readme.md build numbers for status** — git log and HANDOFF's top block are the truth (readme's suite count is stale by ~650 tests).
- **Debugging from a worktree with root-relative assumptions** — shared root .venv, CWD-relative registry paths, and pytest running the WORKTREE's code when invoked from the worktree root.
- **Concluding corroboration is satisfied because k≥3 netlocs appear** — wire syndication fakes distinctness (open F72); 3 syndicated copies of one press release are one publisher in spirit and the gate cannot tell (gate-integrity-campaign).

## Provenance and maintenance

Authored 2026-07-05 against the library baseline main @ a8ec757; every code fact re-verified
same day at main @ 11ffd61 (working tree clean; the F74 incident's tree damage was resolved by
the d9cfb3f daily-run commit; at that snapshot the root cause was still unfixed and the fix lane
`.worktrees/f74-cycle-log` was unmerged). **Updated 2026-07-06:** F74 merged same-day as the
11ffd61 snapshot, at `257cf1b` (2026-07-05, backlog ticked `1a9eb33`); the guard is now live in
`cli.py` and the trap does not re-arm on a normal run — the worktree/branch above are deleted.
See desk-failure-archaeology fight 12 for the full chronicle.

Volatile facts and their re-verification one-liners (run from repo root):

| Fact (as of 2026-07-05) | Re-verify with |
|---|---|
| Rejection strings in references/rejection-strings.md | `grep -n "errors.append\|violations.append" gpu_agent/gate.py gpu_agent/extraction/extractor.py gpu_agent/sufficiency.py gpu_agent/judgment/judge.py` |
| Voice-lint fields/caps and banned words | `.venv/Scripts/python -c "from gpu_agent.reader import BANNED_WORDS; print(BANNED_WORDS)"` and read `_voice_lint_samples` in gpu_agent/cli.py |
| Acronym allowlist size (100) | `.venv/Scripts/python -c "import json;print(len(json.load(open('registry/acronyms.json'))['allowed']))"` |
| minDistinctPublishers = 3 | `type registry\corroboration.json` (PowerShell) / `cat registry/corroboration.json` |
| Exit-2 count-error strings | `grep -n "!= documents\|!= samples" gpu_agent/cli.py` |
| Sufficiency inert-without-corpus-store wiring | read gpu_agent/cli.py lines ~776-790 (`pipeline` seam) and ~448-457 (`judge` seam) |
| cycle-plan overwrite (F74 mechanism) | `grep -n "write_text" gpu_agent/cli.py` around `_cycle_plan`; F74 status: `git log --oneline --grep=F74` and `git worktree list` |
| Gitignore whitelist (chips.merchant-gpu only) | `git check-ignore -v store/models.frontier-closed/x.json` (should name `store/*`) |
| F24 wiki fragmentation (nvda/nvidia/multi) | `ls store/wiki/entity/` |
| Mixed-grain store contents | `ls store/chips.merchant-gpu/` |
| Suite size (1063 collected / 1059 pass + 4 skip) | `.venv/Scripts/python -m pytest --collect-only -q \| tail -1` |
| Open F-item statuses cited here (F24, F71-F75) | `git log --oneline --grep="F<nn>"` beats any checkbox |
| python3 stub path | `where.exe python3` |
| scripts/judge_conflicts.py still matches judge internals | run it against `fixtures/recorded/judge-nvda.json` + a one-finding file citing `doc-nvda-1` (see tests/test_cli_judge.py `_clean_finding`) — expect exit 0 |
