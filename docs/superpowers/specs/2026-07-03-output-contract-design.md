# The output contract — renderer structure + analyst voice (F67)

- **Date:** 2026-07-03
- **Status:** Approved design (user-approved in session, 2026-07-03).
- **Parent:** [`2026-06-29-human-market-brief-design-target.md`](2026-06-29-human-market-brief-design-target.md)
  (the five readability rules and the target layout — this spec is their *enforcement*, plus the
  brain-side voice layer the target did not cover); charter Part 35 (the surface is a projection
  consumer), Part 17 (numbers; plain language).
- **Backlog:** logged as **F67** in `docs/fix-backlog.md`. Absorbs **F61** (staleness banner),
  reserves the slot for **F65** (TSMC so-what), aligns the daily shell with **F64**
  (trigger-first daily brief).

## Why this exists

The 2026-07 flagship report violates the design target's own five rules, and the reader feels it
as "scattered":

- **The BLUF is buried** — THE CALLS (nine theses, each with 8+ inline citation ids like
  `[d1io3yog0oux5-cloudfront-net-5283a803-1, …]` and mid-word-truncated excerpts) renders first;
  STATE OF THE MARKET arrives ~40 lines in.
- **Raw internals leak into prose** — `BINDING CONSTRAINT: bottleneck` (the dimension label, not
  the constraint), indicator ids `D2`/`S10` in the demand/supply board, `PMI: —`,
  `Δ vs prior: —` on every price row.
- **Signature sections render empty** — `WHAT MOVED: (no material moves this cycle)`;
  STORYLINES: five bare arrows with no content. The diff-first design reads as a snapshot with
  dead sections.
- **Contradictions ship unexplained** — "Supply: CONTRACTING ▼" directly under a narrative
  saying "Strong, improving"; the same status paragraph appears verbatim twice.

Structure problems belong to the deterministic renderer; insight problems belong to the
brain-written prose. So the contract has two layers (code owns structure, brain owns content —
the repo's standing doctrine split), plus a thin session rule.

## 1. Renderer contract (`report.py`) — one fixed section order

The brief is an inverted pyramid. Every section either earns its place or folds to one honest
line. Order:

| # | Section | Content rules |
|---|---|---|
| 1 | **Header** | Category, `asOf`, Δ-vs-prior pointer, confidence relabeled to what it measures ("vote agreement: high"), and the **F61 staleness banner**: median + oldest evidence date vs `asOf`, share of evidence older than 6 weeks, count of not-covered/paywalled expected sources. |
| 2 | **State of the market** (BLUF, ≤8 lines) | Status + direction; Demand/Supply/Gap words-first with "was X" (bands lead, raw index in parentheses); NOW (Momentum) vs NEXT (Outlook) with any divergence called out on its own ⚠ line; **binding constraint named concretely** — the renderer prints the constraint noun sourced from the bottleneck dimension's structured data (e.g. "CoWoS/HBM3E packaging, 52–78wk lead times"), never a dimension label. If word-band and narrative disagree (e.g. CONTRACTING under "Strong, improving"), render a one-line reconciliation sourced from the scorecard (which side is trailing vs forward), never silently juxtapose. |
| 3 | **What moved** | The diff vs prior leads. Empty state must say *why*: "no material moves vs 2026-06; this cycle's 12 fresh findings were price levels only" — computed from the dedup/findings counts, not a bare "(none)". |
| 4 | **The calls** | One line per thesis: title, verdict arrow, conviction, streak. "breaks if:" on line two. Citations compressed to counts ("9 cites: 3 primary"); full id map in the appendix. No excerpt truncation — render the thesis `statement`, not a clipped evidence excerpt. |
| 5 | **Why (drivers → constraints)** | Kept as the causal tree; one sentence per driver; compressed citations. |
| 6 | **Demand \| Supply board** | Human labels from the registry (`Backlog / RPO`, never `rpoBacklog`; never `D2`/`S10`); words-first signal + direction; per-row recency stamp; single-source ⚠ flags kept. |
| 7 | **So what for TSMC** | Reserved slot; renders when F65 lands; until then the section is omitted entirely (no placeholder text). |
| 8 | **Trust & coverage footer** | Evidence mix (primary/secondary counts), under-supported dimensions, paywalled/not-covered gaps, and the "read DIRECTION, not level" caveat. |
| 9 | **Appendix** (below the fold) | Dimension ratings table, entity panel, price track, full citation map (finding id → source/date/tier). |

Global renderer rules:

- **No raw internal ids above the appendix** (indicator ids, finding ids, storage keys).
- **The constraint noun needs a home:** the renderer cannot invent prose, so judgment emits an
  optional `constraintLabel` string (e.g. "CoWoS/HBM3E advanced packaging") alongside
  `categoryStatus` — additive and optional (absent → the BLUF omits the constraint line rather
  than printing a dimension label). This is the spec's only schema-touching change; it is
  additive-optional and therefore not a frozen-core migration.
- **No paragraph renders twice** — the status reason renders once, in the BLUF.
- **Dead metrics fold** — "PMI: —" and all-dash price deltas collapse into one line:
  "price track: 5 series captured, day-over-day deltas need two matched cycles (F53)".
- The renderer stays a **pure LLM-free projection** (Part 35): same store → same bytes, replays
  for $0.

## 2. Analyst-voice guideline — brain-side, lintable

### 2a. Reader contract (added 2026-07-03, user-directed)

**The reader is a TSMC executive with zero knowledge of this repo.** If a term needs this
project to understand, it does not ship above the appendix:

- **Internal/doctrine/repo vocabulary is banned from the rendered surface** — not just ids:
  index acronyms (DMI/SMI/SDGI/PMI — the word band leads, the acronym may appear once,
  parenthesized, in the appendix), tier jargon ("primary/secondary" renders as "company
  filing / official post" vs "press / analyst report"), status jargon ("grounded" → 
  "well-evidenced", "under-supported" → "thin evidence", "provisional" → "early — not yet
  corroborated"), and process words (gate, vintage, dedup, manifest, registry, lane, cycle
  log). The renderer applies these as a **label map** (code); the brains are instructed the
  same way (prompt).
- **Acronym allowlist, enforced:** only industry-standard acronyms an exec already knows —
  GPU, HBM, CoWoS, ASIC, TPU, AI, capex, YoY, Q1/FY, IR, SEC, 10-Q/10-K, and peers —
  maintained as DATA (one small allowlist the lint reads). Deterministic check: any all-caps
  token in rendered prose above the appendix must be on the allowlist.
- **All prose passes stop-slop.** The tool-less judgment/thesis brains cannot invoke skills,
  so the prompt builders **embed the stop-slop pattern rules** (no "delve / crucial / pivotal /
  robust / landscape", no "not just X but Y", no rule-of-three filler, active voice, concrete
  nouns — the skill's list is the source of truth at plan time); the banned-word subset is
  linted deterministically. The coordinating session **invokes the stop-slop skill** on its
  final human-facing message before surfacing it.

### 2b. Depth rules per field

Lives in the judgment/thesis prompt builders (`--emit-prompt` paths), operationalizing a subset
of Action Item 1's Depth Rubric per output field:

- **Narrative = exactly 3 sentences:** (1) state and why now; (2) the **crux** — the one or two
  questions that decide the next rating change; (3) the **watch item** — what would most likely
  change this picture and where it would show up first.
- **Dimension rationale ≤ 2 sentences**, naming the *deciding* evidence, not enumerating all of
  it.
- **Thesis prose:** claim ≤ 1 sentence, mechanism ≤ 1 sentence (triggers already gated).
- **Ban list in prose:** indicator ids, finding ids, "bottleneck" as the constraint's name,
  fetch dates, and hedge-pairs ("strong but risks remain") unless the same sentence says which
  side wins and why. (The hedge-pair rule is prompt guidance only — not linted; the rest is
  linted.)
- **Deterministic lint** (same shape as the thesis gate): regex for banned id patterns +
  sentence-count caps over narrative/rationales. One re-dispatch on violation, then fail loud;
  the gate never rewrites prose.

## 3. Session-output rule (`run-cycle` skill — one paragraph)

The session's final message = the rendered brief **verbatim** + a ≤3-line run-health footer
(docs gathered/kept, dedup new/update/duplicate counts, caps tripped, stages failed). Gather
logs, prompts, and dedup detail are referenced by path, never pasted into the reader's face.

## 4. Daily brief shares the shell

Same renderer path and section order, two cadences:

- Daily leads with **What moved** (its natural content); the Calls section becomes F64's
  trigger-watch when F64 lands (until then, daily renders the same compressed Calls as the
  monthly).
- One renderer, so monthly and daily cannot drift apart.

## Testing

- **Golden render tests:** fixture scorecard → exact expected text (extend
  `fixtures/report/`).
- **Empty-state test:** a scorecard with no prior, no theses, no price series, no moves — every
  section folds to its one-line honest state; no `—` orphans, no "(none)".
- **Lint unit tests:** banned-id regexes, sentence caps, the re-dispatch path, the
  stop-slop banned-word subset, and the **acronym-allowlist check** (an all-caps token not on
  the allowlist above the appendix fails the render test).
- **Label-map test:** tier/status jargon never appears above the appendix ("secondary",
  "grounded", "under-supported", "provisional" are rendered via the label map).
- **No-duplicate test:** rendered output contains the status reason exactly once.

## Out of scope

- The HTML dashboard (Part 35 pull surface) — after the Markdown content model is proven.
- The layer-tier / cross-cutting market brief (§0 of the parent design target).
- F64's trigger-watch content and F65's TSMC-implications content — this spec only reserves
  their slots in the shell.
- Any change to scoring, gating, or the Finding schema (frozen contract untouched).
