# F62 — Flagship consumes the daily store (design)

- **Date:** 2026-07-04
- **Status:** approved-with-AFK-defaults (see Decision provenance)
- **Branch:** `f62-flagship-consumes-store` (worktree `.worktrees/f62-flagship-store`, off main @ `c4913a6`)
- **Backlog:** docs/fix-backlog.md F62 — highest-leverage item of the 2026-07-03 freshness & exec-gap
  review. Approved sequence position: F6 ✅ → **F62** → F63 → F57/F58/F59 → F60 → F64 → F65 → F66.

## Decision provenance

Brainstormed 2026-07-04 with four user-answered forks and three AFK gates. The user answered
(AskUserQuestion, recorded verbatim):

1. **Corpus depth = full first-class union** — store findings merge with fresh findings into one
   corpus that feeds judge + thesis prompts AND the scorecard (citable, anchor-counted, scored).
2. **Window = fixed N days, default 45** (CLI-overridable), coherent with F58's planned live dial.
3. **Write-back = yes, symmetric** — the standard path gains the dailies' L2-dedup + wiki-ingest steps.
4. **Gather demotion = coverage-report-driven top-up** — code computes coverage; the skill wires it
   (F55 lesson: never coordinator-improvised).

AFK-defaulted to the recommended option (user away at the gate; F52–F54 precedent — relitigate here
if any pick is wrong):

5. **Vintage tag in emitted brain prompts = YES** (`observed=<date>` on judge briefing rows and
   thesis finding rows), accepting one run-eval pass + `eval rebaseline` committed with the prompt
   change (the budgeted F6-gate procedure).
6. **Design approval + spec review gates** ran unattended; execution mode defaults to
   subagent-driven development per precedent. Merge remains blocked on the user's explicit go.

## Problem

Daily mode WRITES fresh findings into the store (`wiki-ingest` → `store/findings/` + wiki
observations), but the standard/monthly path never READS the wiki or `store/findings/` back: the
monthly brief is a projection of one cycle's ≤20 gathered docs, so everything the dailies learned is
discarded at exactly the moment someone reads the output. Recorded smoking gun: the
`vendor-financed-demand-circularity` thesis was proposed from NVIDIA's own official newsroom post in
the 2026-07-01 morning daily and demoted to conviction low by the evening flagship **the same day**
("no primary support") — the flagship's judge/thesis had no citable access to the daily's finding.
The July flagship's freshest substantive evidence was an April filing while `store/findings/` held
Anthropic–Samsung 2nm, NVIDIA vendor-financing, and Digitimes 2H26 signals.

Secondary gap (write side): the flagship's own gated findings (72 in `2026-07-v1`) never reach the
store either — only the scorecard JSON holds them — so the accumulated corpus is daily-only.

## Goal

The standard/monthly cycle judges from everything the system knows: the windowed, gated,
accumulated store corpus plus a coverage-aimed top-up gather. Deterministic code assembles the
corpus and logs every drop; the brains see it as citable DATA; the store accumulates from both
cadences. Dailies are unchanged.

### Success criteria

1. With a non-empty window, the flagship's emitted judge and thesis prompts contain the windowed
   store findings as citable rows, and the scorecard validates citations to them (F35 groups are
   computed over the same merged corpus at emit and at gate time).
2. Corpus assembly writes a merged-corpus artifact, a deduped-fresh artifact, and a CorpusReport;
   every dropped duplicate, skipped page, and out-of-window exclusion is counted in the report and
   printed to stderr — nothing silent.
3. All existing commands are byte-identical without the new flags (test-pinned); the frozen core
   (`gate.py`, `scoring.py`, `schema/*`, `judgment/briefing.py`, `judgment/judge.py` aggregation,
   `pipeline.py`, `JsonStore`) has an empty diff.
4. Suite green at merge; the F6 eval baseline is regenerated via `.claude/skills/run-eval` +
   `gpu-agent eval rebaseline` (never hand-edited), committed WITH the prompt change; per-seam means
   ≥ incumbent (ties pass).
5. Live verification (next monthly cycle): the corpus report shows daily findings entering the
   flagship; gather ran as a top-up with the coverage block in its dispatch; the flagship's fresh
   findings appear in `store/findings/` after write-back; a thesis backed by store evidence can cite
   it (the smoking-gun demotion class is structurally impossible when the evidence is in-window).

## Non-goals (recorded decisions stand — do not relitigate here)

- **F63** corroboration math / evidence-sufficiency gate (F69's chase results stay free text until F63).
- **F59** primary allowlist (store findings keep their stamped tiers; official-post findings stay
  `secondary` until F59 — F62 makes them *citable*, not *primary*).
- **F57** gather slices, per-class floors, threading the L1 seen-doc filter into the standard path.
- **F58** live-mode recency window for *gather queries* (F62's 45-day default is the *corpus* window;
  the numbers are deliberately coherent but the dials are independent).
- **F60** indicator weights; **F24** entity canonicalization (the `NVDA` vs `nvidia` page split is
  visible in the corpus enumeration and tolerated: both pages carry the category and both are read).
- `memory.py` grain semantics: the monthly MEMORY prior remains the prior month-grain scorecard;
  daily scorecards stay out of the monthly bundle (`label < as_of` lexical cutoff unchanged). The
  daily signal reaches the flagship through the corpus findings, the shared thesis book, and wiki
  states — a richer memory block would trip the eval gate for no additional citable evidence.
- Daily-mode corpus judging (dailies already read the store via L2 and write back; unchanged).
- Category namespacing of `store/findings/` (F24/F25 scale-out work).

## Design

### Overview

One new deterministic, read-only module (`gpu_agent/corpus.py`), one new CLI command (`corpus`),
additive flags on `pipeline`, an additive `observed=` date on the two emitted brain-prompt row
formats, and run-cycle skill wiring for the standard path. Zero frozen-core edits: the union enters
through the existing seams (`judge_findings` and `build_scorecard` take plain findings lists;
`dmi_smi_contribution` already collapses to latest-per-`(entity, indicatorId)`, so mixed-vintage
unions score correctly with no double counting; `check_scorecard` gates per-finding with each
finding's own `asOf`).

### gpu_agent/corpus.py (new)

Sibling of `memory.py`: read-only consumer of existing stores, no writes, no clock, byte-identical
outputs for identical inputs. Public surface:

- `WINDOW_DAYS_DEFAULT = 45`.
- `period_end(label: str) -> datetime.date` — day-grain label → itself; month-grain label
  `YYYY-MM` → the last calendar day of that month. Fail loud on any other shape (F56-adjacent
  defense; the seams already require ISO labels).
- **Window rule:** a store finding `f` is in-window for run `as_of` iff
  `period_end(as_of) - window_days < period_end(f.asOf) <= period_end(as_of)`.
  Label-based (no wall clock) so replays/backtests are deterministic and a past cycle never sees a
  future label. A daily finding later in the flagship's own month is in-window by design: the
  month-grain label means "state of that month". Month-grain store findings (post-write-back
  flagship findings) participate via their month's period end.
- `enumerate_store(store_root, category, as_of, window_days) -> (findings, report_fields)` — walk
  `WikiStore.index()`; pages whose `category` == the target contribute their observations'
  findingIds (deduplicated across pages); resolve each through `FindingStore.get` (fail loud on a
  dangling or invalid finding — canonical-store integrity, never skip silently); window-filter.
  Pages with a different or absent `category` are skipped AND recorded (`skippedPages: [{id,
  category}]`). Out-of-window findings are counted (`outOfWindow: <n>`), not listed individually.
  Deterministic order: sort by `(asOf, id)`.
- `assemble(store_root, category, as_of, fresh, *, window_days) -> CorpusResult` —
  1. store part = `enumerate_store(...)`;
  2. fresh part = `classify_findings(fresh, wiki_store)` (the existing L2 machinery, unchanged):
     intra-batch collapse + evidence-merge + dispersion, then cross-store NEW/UPDATE keep vs
     DUPLICATE drop — all classifications carried into the report;
  3. merged = store part + fresh `outFindings`, defensively deduplicated by id (a same-id overlap
     means the identical finding is already stored — keep the store copy, log the event);
  4. no collapse *within* the store part: the store holds only NEW/UPDATE vintages by construction,
     and multiple vintages of one series are deliberate history — scoring takes latest-per-series,
     the judge sees the evolution (now dated). The known effect that a multi-vintage series counts
     more than once in a dimension's *anchor mean* is accepted and documented: the window bounds it,
     same-series vintages almost always share sign, and the F36 gate checks the same corpus-derived
     anchors at emit and at gate time so consistency holds.
- `CorpusResult`: `merged: list[Finding]`, `dedupedFresh: list[Finding]` (= L2 `outFindings` minus
  id-overlaps with the store part — the write-back stream never re-ingests a finding the store
  already holds), `report: CorpusReport`.
- `CorpusReport` (pydantic): `asOf`, `category`, `windowDays`, `windowStart`, `windowEnd`,
  `storeIncluded: list[str]` (ids), `outOfWindow: int`, `skippedPages: list[{id, category}]`,
  `freshNew/freshUpdate/freshDuplicate` (the L2 `FindingClass` lists), `idOverlaps: list[str]`,
  `coverage: list[CoverageEntry]`, `notCovered: list[str]`.
- `coverage(store_findings, registry, category) -> (entries, not_covered)` — per
  `(entity, indicatorId)` over the windowed store part: `count`, `latestAsOf`, `latestObservedAt`;
  `not_covered` = registered indicator ids (for the category, price included) with zero windowed
  findings. `render_coverage_text(...)` — compact deterministic block for the gather dispatch
  (header line naming the window, one line per covered series, one `not covered:` line).

### CLI (cli.py — additive; defaults byte-identical)

New command:

```
gpu-agent corpus --store <root> --category <id> --as-of <asOf> [--window-days 45]
                 [--fresh <findings.json> --out-merged <path> [--out-deduped-fresh <path>]]
                 [--report <path>]
```

- **Store-only mode** (no `--fresh`): prints the rendered coverage block to stdout (the pre-gather
  step); `--report` persists the store-side CorpusReport (empty fresh sections).
- **Assemble mode** (`--fresh`): requires `--out-merged` (exit 2 otherwise); writes the merged
  corpus, the deduped-fresh stream, and the report; prints a one-line count summary
  (`store <n> in-window (<m> out), fresh new <a> update <b> duplicate <c> -> merged <k>`) and every
  skip/drop line to stderr.
- Both modes fail loud (exit 1, offending id named) on store-integrity errors.

`pipeline` gains `--corpus-store <root>`, `--corpus-window-days <n>` (default 45), and
`--corpus-report <path>`. When `--corpus-store` is given, `_pipeline` calls the same
`corpus.assemble(...)` over its own gated extraction output (category from the assignment, asOf from
`--as-of`) and hands the **merged** list to `judge_findings` + `build_scorecard`; the report is
written when a path is given and the count summary always goes to stderr. Because the emit step's
merged file and the pipeline's internal merge are the same deterministic function of the same inputs,
the emitted prompt's anchors/citation groups and the gate's are identical — **provided the session
reuses one `--captured-at` value across `extract --recorded` and `pipeline`** (now load-bearing; the
skill states it explicitly, and the equality is test-pinned). Absent the new flags, `_pipeline` is
byte-identical to today.

`judge`/`thesis` need no new flags — the skill hands them the merged file via the existing
`--findings` parameter.

### Vintage in the emitted brain prompts (the one eval-gated change)

Both emitted row formats gain the finding's observation date:

```
  <id> [<indicatorId>] <statement> (demand=+1 supply=+0 mag=2 conf=medium observed=2026-06-29)
```

- `judgment/prompt.py build_user_prompt(...)` gains `include_dates: bool = False` (F55
  `include_groups` pattern): the CLI emit path passes `True`; the frozen `judge_findings` internal
  path keeps the default and stays byte-identical (test-pinned).
- `thesis.py _finding_lines(...)` changes to the same dated row (its docstring already binds it to
  mirror the judge row format; thesis prompts exist only on the emit path).
- `observed=` uses `f.observedAt[:10]` (the real-world observation date — vintage truth), not
  `asOf` (the cycle label) and not `capturedAt` (the fetch stamp).
- `gpu_agent/evals/emit.py` mirrors the live CLI emit (pinned by the b537444 equality test), so it
  adopts the dated rows in the same commit — mirroring the live seam, never diverging from it.
- **F6 gate procedure:** this turns `tests/test_evals_baseline_pin.py` red. The unlock is running
  `.claude/skills/run-eval/SKILL.md` (re-dispatch brains + graders, all tool-less Opus), then
  `gpu-agent eval rebaseline`, committing the new baseline WITH the prompt change. Comparison rule:
  per-seam mean ≥ incumbent, ties pass. Never hand-edit `fixtures/evals/baseline.json`.

### run-cycle skill wiring (standard path; Daily mode explicitly unchanged)

Step 3 gains, per ready category (names refer to the existing steps):

- **(a0) Coverage before gather:** `gpu-agent corpus --store store --category <id> --as-of <asOf>
  --report <work>/corpus-coverage.json`. If the printed coverage block is non-empty, the
  gather-category dispatch includes it verbatim with top-up framing — *aim at the `not covered`
  list and material updates to covered series; do not re-derive covered ground* — and the doc cap
  for this gather is `min(manifest maxDocuments, 10)`. An empty store means a full gather exactly
  as today.
- **(b)** unchanged, plus one binding sentence: the SAME `--captured-at` value is used for
  `extract --recorded` and `pipeline`.
- **(b2) Corpus assembly after the gate:** `gpu-agent corpus --store store --category <id> --as-of
  <asOf> --fresh <work>/findings.json --out-merged <work>/corpus-findings.json --out-deduped-fresh
  <work>/deduped-fresh.json --report <work>/corpus-report.json`.
- **(c)** judge emit reads `--findings <work>/corpus-findings.json`.
- **(d)** pipeline adds `--corpus-store store --corpus-report <work>/corpus-pipeline-report.json`.
- **(d2) Write-back after a successful scorecard:** `wiki-ingest --findings
  <work>/deduped-fresh.json --store store --as-of <asOf> --category <id>` then `wiki-lint --store
  store --as-of <asOf>`. Skipped (logged) when the scorecard failed — no partial cycle committed as
  complete. Runs strictly after (b2) so classification never sees its own write.
- **(e)** thesis reads `--findings <work>/corpus-findings.json`.
- **(6)** cycle-log records the corpus artifact paths and the count summary (store in-window /
  fresh new / update / duplicate) alongside the existing entries.

### Error handling

- Corrupted store finding, dangling observation id, invalid label shape → fail loud with the id
  named (exit 1). The canonical store is trusted input; corruption is a stop-the-line event, not a
  skip.
- Missing wiki dir / empty store / zero in-window findings → honest empty corpus (merged = fresh),
  logged in the report and stderr; the run proceeds (first-ever cycle degrades to today's behavior).
- `--fresh` without `--out-merged`, unreadable inputs → exit 2 usage errors (matches CLI convention).
- Every skipped page, dropped duplicate, and id overlap is in the report AND stderr.

### Interactions

- **F52 vintage ids** make the union safe: a URL re-gathered by the flagship mints a new-vintage id,
  so store/fresh collisions are content-identical by construction and the L2 classifier (not id
  luck) decides duplicate vs update.
- **L2 dedup state**: `classify_findings` is reused unchanged; the corpus report embeds its
  `FindingClass` lists so the flagship's dedup decisions are as replayable as the dailies'.
- **F61/F67 staleness banner** needs no change: corpus findings raise the median evidence age the
  banner already reports honestly.
- **F63** gets a richer substrate for free (multi-day independent secondary evidence is now in one
  briefing) but no scoring/status change ships here.
- **Concurrent instances**: all F62 work on `f62-flagship-consumes-store`; docs edits minimal and
  re-read right before editing (roadmap/HANDOFF churn expected on main).

## Testing

- **corpus.py units:** `period_end` both grains + rejects; window boundary cases (exactly N days,
  same-day, future label excluded); category scoping (wrong/absent category pages skipped and
  reported); dangling observation fails loud; enumeration determinism (byte-identical report on
  re-run); merge id-dedup; coverage entries + not-covered; honest empties (no wiki, empty window).
- **CLI:** `corpus` flag matrix incl. exit codes and stderr lines; `pipeline` with corpus flags
  produces a scorecard whose findings equal the `corpus` command's merged file given the same
  `--captured-at` (the equality pin); `pipeline` WITHOUT the flags byte-identical (existing recorded
  fixtures); judge emit with `include_dates=False` byte-identical (pins the frozen path);
  `judge --emit-prompt` and `thesis --emit-prompt` rows carry `observed=`.
- **e2e:** fixture store + fresh cycle where the judge's recorded answer cites a store-vintage
  finding: scorecard validates, report renders, citation map resolves.
- **Eval:** one run-eval pass + rebaseline committed with the prompt change (procedure above).
- Suite green at every merge (baseline 923 passed / 3 skipped).

## Frozen-contract compliance

`gate.py`, `scoring.py`, `schema/*`, `judgment/briefing.py`, `judgment/judge.py` aggregation,
`pipeline.py`, `JsonStore`: **zero edits** (final review verifies empty diffs). New code:
`gpu_agent/corpus.py`, additive `cli.py` grammar, additive `judgment/prompt.py` kwarg, the thesis
row helper, skill prose, tests. Doctrine holds: code computes + gates + stores; brains are tool-less
dispatched Opus via `--emit-prompt` → `--recorded`; every cap/skip/drop logged; no hand-edited brain
output or eval fixtures.

## Addendum (2026-07-04, user-approved): judge crux sentence gains consensus-departure

Two full eval attempts failed record-grade on the judge seam only (6.50, 6.25 vs incumbent
6.75) with one signature: all 8 fresh judge generations scored sensitivity-differentiation=1
— the rubric awards 2 only when the narrative also states where the read departs from
consensus, and the three-sentence narrative spec never asked for it. User chose option B
(fix the prompt/rubric mismatch on the prompt side, keep the rubric): sentence (2) of the
narrative spec now reads "the crux — the one or two questions that decide the next rating
change, and where and why this read departs from the consensus view". Sentence budget stays
exactly three (deterministic lint untouched). This is validated in the same eval cycle as the
observed= tag; rebaseline only on a merit PASS (no --force).
