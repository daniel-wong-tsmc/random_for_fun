# Merchant-GPU Category Agent — Showcase Dashboard

**Date:** 2026-07-06
**Status:** Design — awaiting user review
**Topic:** A reusable generator that turns the daily `report.txt` + dated scorecards into a single self-contained HTML dashboard, written in plain language for a non-specialist reader.

---

## 1. Purpose & audience

Give a viewer who is **not** steeped in the project a fast, honest picture of two things:

1. **The market read** — what the agent currently concludes about the merchant-GPU market (the state of the market, the key claims it is tracking, demand vs supply, the headline indices).
2. **The work behind it** — that this is a repeated, evidence-backed process: how the numbers and claims have moved across the runs so far (2026-07-02, 07-03, 07-05, 07-06).

The viewer is assumed to be smart but new to the domain — e.g. a colleague, a friend, or a reviewer. They should not need to know what "SDGI", "HBM", or "INTACT" mean. Every label the dashboard adds is in **plain, widely-used language**.

Output is a single HTML file that opens in any browser with no server and no internet.

## 2. Non-goals (YAGNI)

- No live/auto-refresh, no server, no database. It is rebuilt on demand by running one command.
- No editing or interactivity beyond hover tooltips and (optionally) collapsing sections. No filtering UI in v1.
- No new data. It only reads artifacts the agent already produces, plus a plain-English overrides file (§4c).
- The **generator itself never calls an LLM** and never edits the source `report.txt`/scorecards. Plain-English rewriting is done by a separate, callable agent (§4c) that writes its output to its own file. This keeps the tool deterministic and the source artifacts intact.
- Not multi-category yet. Scoped to `chips.merchant-gpu`. The design keeps the category id as a parameter so a second category is a small change later, but that is out of scope now.

## 3. Data sources

Two source inputs (below), chosen so the fragile part (text parsing) is minimized, plus one enrichment file — the plain-English overrides written by the §4c agent, which never alters these sources.

### 3a. Dated scorecards — the numeric trend (robust, structured)
`store/chips.merchant-gpu/YYYY-MM-DD-v*.json`, one per cycle. Currently: `2026-07-02-v1`, `2026-07-03-v1`, `2026-07-05-v1`, `2026-07-06-v1`. Confirmed identical key structure across all four. Fields used:

- `asOf` — the cycle date (x-axis of every trend).
- `indices` — `momentum.dmiContribution`, `outlook` contributions, `divergence.state`/`sdgiGap`. (Headline demand/supply/gap numbers.)
- `demandSupply` — `dmiContribution`, `smiContribution`, `sdgi`, `sdgiDirection`, `anchors` (per-dimension pulls).
- `categoryStatus` — `rating`, `direction`, `bottleneck`, `reason` (the one-paragraph state-of-market).
- `dimensionRatings` — dict keyed by dimension → `rating`, `direction`, `confidence.level`, `rationale`.
- `dimensionStatus` — dict keyed by dimension → `evidenceStatus` (grounded / under-supported), `findingCount`, `confidenceCap`.
- `findings` — each carries the fields the ranking needs (§4b): `statement`, `observedAt` (evidence date), `magnitude` (1–3 impact weight the agent already assigns), `impact.direction` (positive / negative / mixed), `impact.mechanism`, and `evidence[].tier` (primary / secondary). Count + primary/secondary split come from these.
- `sources` (count + list), `confidence.level`.

When a field is missing on an older scorecard, access is guarded (`.get(...)`) and the section degrades to "not recorded this cycle" rather than erroring.

### 3b. Latest `report.txt` — "the calls" / key claims (only source for this)
`work/daily-*/report.txt`, most recent by folder date. The per-cycle **status of each tracked claim** (still-holds vs being-questioned, getting-stronger/weaker, confidence, how many runs tracked, the "breaks if" trigger) is rendered **only** in `report.txt`; the scorecards do not carry it, and the registry holds only the current snapshot without history. So the generator parses the `THE CALLS` block of the latest report. Parsing is best-effort and fails soft (§8).

Line shape (from 2026-07-06):
```
  ● Export control exposure   INTACT, reaffirmed =  (high, 2 cycles)
      Export-control policy materially constrains addressable merchant-GPU demand.  (1 source)
      breaks if: Commerce removes H200 China case-by-case licensing ...
```

## 4. Plain-language principle (the core requirement)

**Every string the dashboard authors is plain and passes an AI-writing-tell check** (via the `stop-slop` skill when writing copy): no "delve / leverage / seamless / robust / boasts / in today's fast-paced", no rule-of-three padding, no reflexive hedging, no em-dash overuse. Short, concrete, human.

**Two kinds of text, handled differently:**
- **Labels, section titles, legends, status/confidence words** → translated by the generator from a fixed dictionary (table below). Deterministic; the reader never sees a raw acronym as a primary label.
- **The agent's own analytical sentences** (`categoryStatus.reason`, each dimension's `rationale`, each claim's one-line statement, each finding's `statement`) → **rewritten into plain, human English** by the separate plain-language writer agent (§4c), not shown verbatim. The generator displays the rewritten version. Where no rewrite exists yet for a given sentence, the generator falls back to deterministic term-swap from the §4a dictionary and flags the item as "auto-simplified — pending human rewrite," so the gap is visible and honest rather than silently jargon-y.

The §4a dictionary still powers the generator's own labels and the always-visible "Plain-language guide" panel; the agent in §4c uses the same dictionary as its baseline vocabulary so the two stay consistent.

### 4a. Translation table (internal term → what the dashboard shows)

| Internal / source term | Plain-language label shown | One-line tooltip |
|---|---|---|
| DMI (demand momentum index) | **Demand momentum** | Is buyer demand speeding up or slowing down |
| SMI (supply momentum index) | **Supply momentum** | Is available supply expanding or tightening |
| SDGI (supply–demand gap index) | **Demand-vs-supply gap** | How far demand is outrunning supply |
| PMI (price overlay) | **Price direction** | Are GPU rental prices rising or falling |
| momentum (index leg) | **Right now** | What the latest signals say today |
| outlook (index leg) | **Looking ahead** | What signals imply for the next quarter+ |
| divergence: diverging-strengthening | **Gap is widening** | Demand pulling further ahead of supply |
| sdgiDirection: demand-led / supply-led / balanced | **Driven by demand / by supply / balanced** | Which side is moving the gap |
| binding / bottleneck constraint | **Main limiting factor** | The one thing capping growth right now |
| categoryStatus rating (Strong/Mixed/Weak) | Strong / Mixed / Weak (kept) | Overall standing of the market |
| direction (improving/worsening/stable) | Improving / Worsening / Steady | Which way it is trending |
| dimension: momentum | **Demand & pricing trend** | — |
| dimension: unitEconomics | **Profit economics** | — |
| dimension: competitiveStructure | **Competition** | — |
| dimension: moat | **Durability of the lead** | How hard the leader is to displace |
| dimension: bottleneck | **Supply bottleneck** | — |
| dimension: strategicRisk | **Big-picture risks** | — |
| grounded | **Backed by evidence this run** | — |
| under-supported | **Little evidence this run** | Not enough new data this run to rate |
| confidenceCap | **Confidence limited to …** | — |
| "the calls" / thesis | **Key claims we're tracking** | Each is a testable statement about the market |
| INTACT | **Still holds** | Evidence keeps supporting it |
| CHALLENGED — pending confirmation | **Being questioned** | One reversal seen; needs another to flip |
| reaffirmed = | **Reconfirmed** | Unchanged this run |
| strengthened ▲ | **Getting stronger** | — |
| weakened ▼ | **Getting weaker** | — |
| not yet judged / 0 cycles | **Too new to rate** | — |
| conviction high/medium/low | **Confidence: high/medium/low** | How sure we are |
| N cycles | **Tracked for N runs** | — |
| "breaks if …" | **We'd change our mind if …** | The trigger that would overturn the claim |
| early — not yet corroborated | **Early signal (one source)** | Seen once; not yet independently confirmed |
| primary (evidence) | **Official source** | Company filing or regulator |
| secondary (evidence) | **News & analysis** | Press or analyst coverage |
| findings | **Evidence points** | — |
| merchant GPU | **Open-market GPUs** | Chips sold to anyone, vs. designed for one company's own use |
| HBM | *(tooltip only)* | High-bandwidth memory — the specialized memory AI chips need |
| DRAM | *(tooltip only)* | Standard computer memory |
| NVMe | *(tooltip only)* | Fast storage drives |
| CoWoS | *(tooltip only)* | Advanced chip packaging that stacks chip and memory together |
| neocloud | *(tooltip only)* | Companies that rent out GPUs by the hour |
| take-or-pay | *(tooltip only)* | Pay-whether-or-not-you-use-it contracts |
| vendor-financed demand circularity | *(tooltip only)* | The chipmaker helping fund its own customers' purchases, which can inflate apparent demand |
| export control | *(tooltip only)* | US limits on selling advanced chips to China |
| hyperscaler | *(tooltip only)* | The largest cloud companies |
| custom ASIC | *(tooltip only)* | A custom AI chip a company designs for its own use |
| CUDA lock-in | *(tooltip only)* | The leader's software that keeps customers on its chips |

The jargon list lives in one dictionary at the top of the generator so it is easy to extend as new terms appear in future reports.

## 4b. Importance ranking — ordering by what matters most

There is a lot to show, so **every list is ordered most-important-first**, and each item wears small badges saying *why* it ranked where it did (no black box).

### Signals (all from real fields, §3a)
Three signals, matching the user's stated priorities:

1. **New** — how recent the evidence is. From `observedAt` vs the cycle date: evidence from within the run's recency window (≤ ~7 days) scores highest; the score decays linearly to zero at 6 weeks (mirrors the report's own "0% older than 6 weeks" line). A finding the dedup step marks as genuinely new (not an update of a prior one) gets a small extra bump.
2. **Official** — is it from an official source. `primary` evidence (SEC filing, company/regulator post) scores full; `secondary` (news/analyst) scores partial. A finding with any primary evidence counts as official.
3. **Impact** — how much money/scale is at stake. Primarily the agent's own `magnitude` (1–3), normalized. A small extra bump when the statement contains an explicit large figure (a dollar amount ≥ $1B or a large unit count like "200,000 GPUs"), detected by a simple number/currency scan.

### Score
```
importance = W_NEW*new + W_OFFICIAL*official + W_IMPACT*impact     # each term normalized to 0..1
```
Because it is a weighted sum, **any single strong signal floats an item up** — which matches "important if it's new, OR official, OR high-impact." Default weights follow the stated priority order and live in one constant block at the top of the script, easy to retune:

```
W_NEW = 0.40   # newest first
W_OFFICIAL = 0.35   # then official sources
W_IMPACT = 0.25   # then monetary/scale impact
```
Ties break by New, then Official. (Open decision in §10: weighted-sum vs strict priority tiers — weighted-sum is the default.)

### Transparency badges (plain language)
Each ranked item shows up to three chips so the order is self-explaining:
- 🆕 **New** (when the New signal is high / flagged new by dedup)
- 🏛 **Official source** (when backed by primary evidence)
- 💲 **High impact** (when `magnitude` is top-tier or a large figure was detected)

A one-line caption on each ranked list reads: *"Sorted most important first — newest, official-source, and highest-impact items rise to the top."*

### What gets ranked
- **Top signals** section (new; see §5) — the findings, ranked directly by this score.
- **Key claims** section — cards ordered by this score (a claim's signals are derived from its supporting findings: *moved this run* → New; *backed by an official source* → Official; *aggregate magnitude / conviction* → Impact). This **replaces** the earlier "group by confidence" ordering; confidence stays visible as a chip.
- **Sources** — primary first, then most recent (a simple projection of the same New + Official signals).

## 4c. Plain-language writer agent (separate, reusable, callable)

A dedicated subagent whose only job is to turn the project's jargon-heavy analytical prose into plain, human English. It is **general-purpose** — the dashboard is its first consumer, but it is built to rewrite any batch of the project's text going forward (briefs, summaries, future dashboards). It is invoked on demand; it is not part of the automatic cycle and never blocks a run.

### Where it lives
`.claude/agents/plain-language-writer.md` — a Claude Code subagent definition (frontmatter: `name`, `description` = when to call it, `tools: Read, Grep, Write`, model). Invoked via the Agent tool ("rewrite the latest merchant-gpu run into plain English") or, later, a thin convenience skill. Because *Claude Code is the brain*, the rewriting is model work done by this agent — the Python tool stays LLM-free.

### Contract (its system prompt encodes these rules)
- **Audience:** a sharp reader with no domain background (a colleague or friend). If they'd need to look a word up, it does not belong.
- **Rewrite, don't just swap words:** restructure the sentence so it reads like a person wrote it. Expand or replace every acronym/jargon term using the §4a dictionary as the baseline, and simplify sentence shape.
- **Preserve meaning exactly:** keep every number, date, company name, and direction (up/down, helps/hurts) precisely. Keep any hedging ("alleged", "not yet confirmed") — do not launder uncertainty into false confidence.
- **No AI writing tells:** obey the `stop-slop` skill — no "delve/leverage/seamless/robust", no rule-of-three padding, no throat-clearing, restrained em-dashes. Short, concrete sentences.
- **In the user's voice:** match the calibrated `voice-profile.md` (§4d) when present — subordinate to accuracy and the plain-language rules.
- **Honesty:** if a source sentence is too vague to rewrite faithfully, it says so in a `note` rather than inventing detail.

### Input / output (the interface — a separate file, never overwrites originals)
- **Input:** the source fields for one cycle, gathered by the agent from the scorecard + `report.txt` (it reads them; it does not modify them).
- **Output:** a standalone overrides file, one per cycle, e.g. `store/chips.merchant-gpu/plain-language/<YYYY-MM-DD>.json`:
```json
{
  "categoryId": "chips.merchant-gpu",
  "asOf": "2026-07-06",
  "sourceRefs": { "report": "work/daily-2026-07-06/report.txt",
                  "scorecard": "store/chips.merchant-gpu/2026-07-06-v1.json" },
  "generatedBy": "plain-language-writer",
  "rewrites": {
    "stateOfMarket":                       { "original": "…", "plain": "…" },
    "dimension.bottleneck.rationale":      { "original": "…", "plain": "…" },
    "claim.export-control-exposure.statement": { "original": "…", "plain": "…" },
    "finding.appleinsider-com-82378946-2026-07-06-1.statement": { "original": "…", "plain": "…", "note": "" }
  }
}
```
Each entry stores the **`original` alongside the `plain`** so the generator can detect drift: if a source sentence no longer matches the stored `original`, the override is stale → the generator falls back to auto term-swap and flags "pending human rewrite." This keeps the two files decoupled and makes staleness visible instead of silent.

### Keys are stable ids
`stateOfMarket`, `dimension.<name>.rationale`, `claim.<slug>.statement`, `finding.<id>.statement` — derived deterministically from the source so the writer agent and the generator agree without coordination.

## 4d. Voice calibration — learning how *you* write

The writer agent does not just write generic plain English; it writes in the **user's own voice**, learned from samples of the user's past writing. This is in-context learning from examples — no fine-tuning, no API training.

### Easy input: drop samples in a folder
- `.claude/agents/plain-language-writer/voice-samples/` — the user drops past conversation histories / writing samples here as `*.md` or `*.txt` files (one file per conversation/sample; or paste everything into a single `samples.md`). A short `README.md` in the folder says exactly that: *"Paste chats or things you've written here. The writer learns your style from them."* This is the "section where I can easily input past conversation histories."

### Calibrate: distill an editable voice profile
- A distinct invocation — the agent in **calibrate mode** — reads every file in `voice-samples/` and writes `.claude/agents/plain-language-writer/voice-profile.md`, an **editable** profile with two parts:
  1. **Traits** — typical sentence length and rhythm, contractions, punctuation habits (em-dashes? lists? parentheticals?), vocabulary the user favors/avoids, formality, how they open and close, recurring quirks.
  2. **Pinned examples** — 2–3 short verbatim snippets that best capture the voice, used as few-shot anchors.
- Re-run calibrate whenever samples are added. The user can hand-edit `voice-profile.md` afterward — it, not the raw samples, is the source of truth the rewriter reads.

### How the rewriter uses it
Every rewrite loads `voice-profile.md` and matches the described voice and the rhythm of the pinned snippets — **subordinate to the hard rules**: accuracy and preserved meaning/numbers come first, then plain-language + `stop-slop`, then voice. Precedence is explicit so voice-matching can never distort a fact or smuggle in jargon.

### Guardrails
- **Style, never content.** The agent learns *how* the user writes, never *what* the samples say. No fact, opinion, name, or phrase-with-content from the samples may appear in a rewrite; rewrite content comes only from the source analytical text. The agent's prompt states this explicitly.
- **Privacy / local-only (default).** `voice-samples/` is **gitignored** by default so private conversation histories are never committed to this public repo. `voice-profile.md` is also gitignored by default (it contains short excerpts); the user can opt to commit it if comfortable (§10). Absent a profile, the rewriter falls back to neutral plain English and notes that calibration has not been run.

## 5. Dashboard layout

Single page, top to bottom, responsive, works in light and dark. Sections:

1. **Header** — "Merchant-GPU Market — Agent Dashboard", the latest run date, how many runs so far, and a "generated on" stamp (`datetime.now()` at build time).
2. **Headline band** — the overall standing (`Strong · Worsening`), the **Main limiting factor** in plain words, and the one-paragraph state-of-market in **plain English** (from the §4c rewrite; auto-simplified with a "pending human rewrite" flag if not yet rewritten). Three tiles: **Demand momentum**, **Supply momentum**, **Demand-vs-supply gap**, each with the latest value, the change vs the previous run, and a tiny sparkline over all runs.
3. **How the numbers moved** — one line chart with the three indices across the four run dates. Plain axis labels; a plain-language caption stating what "up" means for each line.
4. **Top signals — most important first** — the run's findings ranked by the §4b score. Each row: the statement in **plain English** (from the §4c rewrite; auto-simplified fallback if not yet rewritten), its **🆕 New / 🏛 Official source / 💲 High impact** badges, the evidence date, the source name, and an impact-direction marker (helps / hurts the market). This is the section that makes the ranking visible and puts the strongest evidence at the top.
5. **Key claims we're tracking** — the centerpiece. One card per claim from the latest report: plain title, a status chip (**Still holds** / **Being questioned** / **Too new**), a direction chip (**Getting stronger/weaker/Reconfirmed**), **Confidence: high/med/low**, **Tracked for N runs**, the one-line claim in **plain English** (§4c), source count, the same 🆕/🏛/💲 badges, and a collapsible "**We'd change our mind if …**" line. **Ordered most-important-first by the §4b score** (not by confidence; confidence stays visible as a chip).
6. **Demand vs supply** — from `demandSupply`: which side is winning, the gap, and "Right now" vs "Looking ahead". A simple two-bar or gap visual, not a raw number dump.
7. **Where the evidence is strong (and thin)** — the six dimensions with plain names, rating, trend arrow, and a **Backed by evidence / Little evidence** badge. Makes the honesty visible.
8. **What we've done so far** — a compact run strip: for each run date, evidence-points count and sources count, so the "repeated process" story is concrete. This is the "system's work" trend the user asked for.
9. **Plain-language guide** — the always-visible glossary (subset of §4a) and a one-line, honest caveat about reading direction over absolute level (mirrors the report's own "read direction, not level" note).

## 6. Visual approach

- **Self-contained**: all CSS and JS inline; charts are hand-rendered **inline SVG** (no chart library, no CDN) so the file works offline and could later be published as an Artifact under its strict content policy.
- **Charts** follow the `dataviz` skill: restrained categorical palette, readable in light/dark, direct labels over legends where possible, honest axes (no truncation that exaggerates moves), and a caption that states the takeaway.
- **Theme-aware** via `prefers-color-scheme`.
- Tooltips are native `title`/CSS hover — no dependency.

## 7. Build flow

Two decoupled steps — the language step (Claude, on demand) and the render step (deterministic tool):

**Step 0 — calibrate voice (once, and whenever you add samples):**
Drop writing samples into `.claude/agents/plain-language-writer/voice-samples/` and run the agent in calibrate mode to (re)write `voice-profile.md` (§4d). Optional but recommended before the first rewrite; skip it and rewrites use neutral plain English.

**Step 1 — rewrite prose to plain English (Claude, when the source text is new/changed):**
Call the `plain-language-writer` agent (§4c) on the latest run. It reads the scorecard + `report.txt` (and `voice-profile.md` for voice), writes `store/chips.merchant-gpu/plain-language/<date>.json`. Skipped when that file already covers the current run's text (drift-checked via the stored `original`). Never edits source artifacts.

**Step 2 — render the dashboard (deterministic, one command):**
- Generator: `scripts/build_dashboard.py` (standard-library Python only, LLM-free; run from the worktree via `../../.venv/Scripts/python`, or `py -3`).
- Output: `docs/dashboard.html` (single self-contained file).
- Run: `../../.venv/Scripts/python scripts/build_dashboard.py`. It auto-selects the latest `report.txt`, every dated scorecard, and the matching plain-language file; for any sentence without a fresh rewrite it uses the auto term-swap fallback and marks it "pending human rewrite." Prints a one-line summary: runs loaded, claims parsed, rewrites applied / auto-simplified, output path.
- Optional flags: `--category chips.merchant-gpu` (default), `--out docs/dashboard.html`, `--report <path>`, `--plain <path>`.

So the dashboard always renders with one command; the plain-English pass is an independent enrichment that Claude refreshes when the prose changes.

## 8. Robustness / failure modes

- **Missing scorecard field** → `.get(...)` guards; the affected tile/row shows "not recorded this run".
- **`report.txt` calls block unparseable** (template changed) → the claims section shows an honest "Couldn't read the claims list from this run's report" note and the rest of the dashboard still renders. The script prints `claims parsed: N` so a zero is obvious.
- **Only one run present** → trends/sparklines collapse to a single point and the "change vs previous" is shown as "first run".
- **Plain-language file missing or stale** (no §4c rewrite yet, or source text drifted from the stored `original`) → generator uses the deterministic term-swap fallback and marks the item "pending human rewrite." Never blocks the render.
- **Unknown jargon term** in the term-swap dictionary → left as-is (never a crash); adding it is a one-line change to the shared dictionary.
- All file reads are UTF-8 with `errors="replace"` (console is cp1252 per environment).
- **Reproducibility caveat:** the "Key claims" section is sourced from `work/daily-*/report.txt`, which is gitignored. Rebuilding on a machine (or clean checkout) where that run's `work/` is absent yields an empty claims section (graceful, not a crash — `claims=0`). Build the dashboard **in place, immediately after a cycle**, when `work/` exists. The committed `docs/dashboard.html` is the shareable snapshot; treat it as the artifact of record.

## 9. Testing / verification

- **Unit**: the `report.txt` claims parser and the scorecard trend loader each get a small test against the real committed fixtures (2026-07-05 / 07-06 report, the four scorecards), asserting expected counts (e.g. 15 claims on 07-06) and that no jargon acronym appears as a *primary label* in the output HTML.
- **Ranking**: a test on the §4b score that a known primary-source, high-`magnitude`, recent finding (the SEC 8-K vendor-financing item) ranks above a stale secondary low-`magnitude` one, and that the badge set matches the signals.
- **Slop check**: a test that scans the generated HTML against a small denylist of AI-tell words / raw jargon acronyms and asserts none appear as primary text (labels or rendered plain-English prose).
- **Plain-language wiring**: a test that when a plain-language file is present its `plain` text is rendered (not the `original`), and when it is missing/stale the item falls back and is marked "pending human rewrite."
- **Voice plumbing + guardrails**: a test that `voice-samples/` (and, per §10, `voice-profile.md`) are gitignored, and a guardrail check that no distinctive content string taken only from a voice sample appears in a produced rewrite (style-not-content). Voice *fidelity* itself is verified by human eyeball (the `verify` skill), not asserted in a unit test.
- **End-to-end**: refresh the plain-language file for the latest run via the §4c agent, run the generator, confirm `docs/dashboard.html` is produced, open it, and eyeball all nine sections render with real, plain-English data (per the `verify` skill).

## 10. Open decisions (resolved defaults, flag if you disagree)

- **Output location**: `docs/dashboard.html` (chosen; sits with other docs, easy to commit). Alt: repo root.
- **Trend window**: all available runs (currently 4). No cap.
- **Ranking method**: weighted sum (any strong signal floats an item up), weights `New 0.40 / Official 0.35 / Impact 0.25` in one editable constant block. Alt considered: strict priority tiers (all New items above all Official above all Impact) — rejected as too rigid, but a one-line change if you prefer it.
- **Sections collapsible**: v1 renders all expanded except each claim's "We'd change our mind if…" trigger, which is collapsed to keep the claims scannable.
- **Plain-language file location**: `store/chips.merchant-gpu/plain-language/<date>.json` (chosen; per-cycle, committed with other `store/` artifacts, clearly separate from scorecards). Alt: under `docs/`.
- **Rewriter as agent vs skill**: v1 ships the `.claude/agents/plain-language-writer.md` subagent (callable now). A thin convenience skill to wrap it can follow if you want a one-word trigger.
- **Voice files & privacy**: raw `voice-samples/` gitignored by default (private chats never committed). `voice-profile.md` also gitignored by default; flip it to committed if you want the voice shared across instances/machines — your call, since it holds short excerpts.
- **Not committed by the agent**: per the user's global rule, the agent creates files but does not `git add`/commit unless asked. (Work stays on the `dashboard-showcase` lane per repo coordination rules.)
