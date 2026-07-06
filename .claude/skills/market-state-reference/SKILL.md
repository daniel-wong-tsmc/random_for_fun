---
name: market-state-reference
description: Use when reading or reviewing this desk's Findings, scorecards, anchors, rating words, DMI/SMI/SDGI, thesis verdicts, or wiki pages and needing the domain meaning; when gate output says "contradicts anchor", "secondary-only evidence cannot support high confidence", "insufficient evidence", or "affects neither demand nor supply track"; or when unsure about measured/observed/hypothesis, evidence tiers, polarity/magnitude, observedAt vs capturedAt, provisional vs registered, canonical vs ad-hoc, under-supported dimensions, thesis deferrals, or paywalled sources.
---

# Market-State Reference — the domain-theory pack

## Overview

This desk produces **explainable judgments, not numbers**: every output is a gated Finding with a
why, a source, a confidence, and a vintage, and every rating is a plain word bounded (never chosen)
by code. This skill defines what the domain concepts mean *as implemented here* — read it before
interpreting or reviewing any Finding, scorecard, index, or thesis.

## When to use / when NOT to use

**Use when** you need the meaning of a term, field, rating, index, or gate rule — "why is Mixed
allowed here?", "what is an anchor?", "why did this thesis defer?", "can I fetch this source?".

**Do NOT use for:**
- Changing anything defined here (schema, gate rules, weights, thresholds) → **desk-change-control**.
- Triaging a failing run or a rejection loop → **desk-debugging-playbook**.
- Running a cycle / dispatch choreography → **desk-run-and-operate**.
- Eval mechanics, fixtures, what counts as test evidence → **desk-validation-and-qa**.
- Why the design is shaped this way (seams, invariants, stubs) → **desk-architecture-contract**.
- The live F74/F71/F75/F72 gate-integrity work → **gate-integrity-campaign**.

All counts and statuses below are date-stamped 2026-07-05. Charter line numbers drift — trust Part
numbers, re-grep before quoting.

## 1. The market model

- **The 5-layer cake** (Jensen Huang's): Energy → Chips → Infrastructure → Models → Applications.
  Machine-readable contract: `docs/taxonomy.json` — 5 layers, **34** leaf categories (7/7/6/7/7).
  Never say 33. Category ids are `<layer>.<category>`, e.g. `chips.merchant-gpu`.
- **Three analyst tiers** (charter Part 3): 34 Category "desk analysts" → 5 Layer "sector leads" →
  1 Main "head of research". **v1 runs the Category tier only**; Layer and Main are deferred stubs
  (Part 38) — `cycle-plan` hardcodes them deferred (`gpu_agent/cycle.py`).
- **Live today (2026-07-05):** `chips.merchant-gpu` is the only category that has ever produced live
  scorecards (`store/chips.merchant-gpu/`). `models.frontier-closed` is **runnable-per-pins, never
  yet run live** — it has an assignment and manifest but no store directory, and `store/` for it is
  NOT in the `.gitignore` whitelist today (only `!store/chips.merchant-gpu/` is): a first live run
  would write into an ignored path unless `.gitignore` is amended first (route via desk-change-control).
- **Roll-up doctrine** (Part 17): a category's overall rating is an analyst read of its six
  dimensions, **not an average**; a layer is rated by its **weakest link**; the whole market gets one
  of five status words — Accelerating | Healthy | Constrained | Frothy | At-risk — always with the
  bottleneck, the direction, and a one-line reason. No composite number, ever.

## 2. The six dimensions and the rating-anchor system

The six dimensions (frozen list, `gpu_agent/schema/scorecard.py::DIMENSIONS`):

| Dimension | What it rates | Inverted? |
|---|---|---|
| `momentum` | Growth rate of the category's core quantity, right now | no |
| `unitEconomics` | Margin / cost-per-unit trajectory | no |
| `competitiveStructure` | Concentration and pricing rationality of the field | no |
| `moat` | Switching cost / lock-in — tested against a real alternative? | no |
| `bottleneck` | Is this category the gating layer right now? | **yes** |
| `strategicRisk` | Geopolitical / regulatory / capital / circular-financing exposure | **yes** |

A judgment is **three separate fields**: rating (five plain words: Very strong · Strong · Mixed ·
Weak · Very weak), direction (improving | steady | worsening), confidence (low | medium | high) —
plus cited finding ids and a rationale. Never a composite score, never a 0–100.

**The anchor system** (`docs/rating-anchors.md`, F39 — read it in full before reviewing ratings):

1. **Code computes a deterministic anchor per dimension** (`gpu_agent/judgment/briefing.py`):
   group gated findings by their indicator's registry-declared dimension, then
   `anchor = mean over the group of (polarity-on-track × magnitude / 3)`, where the track is
   `registry/indicators.json` top-level `dimensionTracks` (F9 — never derived from finding order).
   Today: momentum/unitEconomics/competitiveStructure/moat/strategicRisk read the **demand**
   polarity; bottleneck reads **supply**. Anchors live in `[-1, +1]`.
2. **The anchor BOUNDS the word; it does not choose it** (`gpu_agent/gate.py`, `_ANCHOR_TOL = 0.15`,
   tightened from 0.5 by F36): Very strong/Strong require anchor > −0.15; Weak/Very weak require
   anchor < +0.15; **Mixed is always allowed**. Within the band, the judge's words decide, using
   rating-anchors.md's falsifiable discriminators ("you should be able to point at…"), never adverbs.
3. **The inversion** (rating-anchors.md states it twice): for `bottleneck` and `strategicRisk`,
   "Very strong" rates the **presence of the factor itself** — a very strong choke point, very high
   risk exposure. It is not a compliment. The other four rate the category's position.
4. **Don't smuggle trend into the word**: "Weak, improving, medium confidence" is a legitimate
   judgment — weak position, getting better.

**Confidence is words, capped by evidence, never invented** (`gpu_agent/judgment/judge.py`):
unanimous 3-sample vote → high, majority → medium; then capped at the best cited finding's own
confidence (`_confidence_ceiling`); then `pipeline.py` F3 caps any rated dimension whose cited
findings carry no primary evidence to medium ("secondary-only evidence"); any under-supported
dimension caps the scorecard's overall confidence high→medium.

**Aggregation facts worth knowing** (judge.py): quorum is `n//2+1` of the (default 3) independent
samples; a dimension below quorum is dropped into `belowQuorum` — "1-of-3 is not unanimity, it is
absence" (F19); majority **ties break toward the weakest rating** (`RATING_ORDER` starts at
"Very weak"); `categoryStatus.bottleneck` must name one of the six dimensions, while
`constraintLabel` is the plain-language constraint (≤6 words, never a dimension name).

See `references/worked-example.md` for the live 2026-07 flagship's anchors → ratings → indices,
traced end to end.

## 3. Finding semantics

A **Finding** (charter Part 2; `gpu_agent/schema/finding.py`) is the atomic unit — everything above
it is a collection of Findings. Three kinds:

| kind | value | evidence | reasoning | confidence ceiling |
|---|---|---|---|---|
| `measured` — a sourced number | required | required ≥1 | optional | high |
| `observed` — a qualitative read | **must be null** | required ≥1 | optional | high |
| `hypothesis` — inferred/predicted | null | optional | **required** | **medium** (gate-enforced) |

Every kind requires statement, why, impact (targets + direction + mechanism), confidence, asOf.
The two cardinal sins (Part 8): **orphan numbers** (a value with no why/source) and **invented
numbers** (a made-up figure to look quantitative). A missing number is honest; a made-up one is
disqualifying.

- **Evidence tiers are code-stamped, never model-chosen** (F2d): `tier` is stamped from the
  document's tier at ingest — primary iff the host matches the manifest's primary domains (CLI
  default `sec.gov`), else secondary. The draft models `extra="forbid"` any model-supplied `tier`
  or `side`. Side is stamped from the registry spec (F37 — registry is the side authority).
- **Confidence-as-words, capped by evidence**: secondary-only evidence cannot carry high confidence
  unless it spans ≥3 distinct publishers (gate F2e, contract v1.3 — see §6). Hypotheses cap at
  medium, always.
- **Dispersion**: when sources conflict, the range + a note goes in `dispersion` — never silently
  pick one (Part 1). The L2 dedup layer sets `dispersion` automatically when same-key findings in a
  batch disagree (`gpu_agent/gathering/dedup.py`).
- **Vintage honesty** (F17): every Finding carries its own `asOf`; `observedAt` = when the fact
  occurred; `capturedAt` = when WE ingested it. Backtests replay on `capturedAt` so the past cannot
  see the future (Part 24). `evidence.date` is the document's **publication** date, never the fetch
  date; dates must be ISO; evidence dated after `asOf` is rejected (grain-aware lexical compare).
- **Excerpts are receipts** (F2b/F2c): `evidence.excerpt` must be a verbatim (whitespace-folded)
  substring of the source document, and `evidence.url` must be the document's own URL. Evidence may
  never cite the dashboard's own output (no self-reference).

## 4. Polarity, magnitude, and the indices

Every canonical Finding declares its demand/supply read (schema v1.1, additive):

- `side` — demand | supply | price | structural: which track it primarily feeds.
- `polarityDemand` / `polaritySupply` — each −1|0|1. **Dual-polarity is deliberate**: one
  observation can move both tracks (HBM price +435% = supply tightness AND downstream cost
  pressure). At least one must be non-zero — except static price levels (trend unknown), which must
  carry 0/0 (F8: a level without a baseline is not momentum).
- `magnitude` — 1|2|3 = slight | significant | severe (charter Part 2).

**DMI / SMI** (Demand/Supply Momentum, `gpu_agent/scoring.py` — frozen, 24 lines): bucket findings
by (entity, indicatorId), keep only scoring non-price/non-structural indicators (per the REGISTRY's
side), take the latest per bucket, then `DMI += weight × polarityDemand × magnitude/3` (same for
SMI with polaritySupply). **SDGI = DMI − SMI**: positive = demand outrunning supply (shortage
forming); direction word at ±0.02 (`pipeline.py`). Price and structural findings NEVER feed the
indices — price is a confirmation overlay (PMI, `price_track.py`, rendered beside, never blended).

**Momentum vs Outlook** (`pipeline.py`): findings are partitioned by their indicator's registry
`cadenceHorizon.horizon` — leading → **Outlook**, coincident/lagging → **Momentum** — and each
bucket is scored by the same frozen formula, plus a divergence state (aligned /
diverging-weakening / diverging-strengthening / insufficient-coverage).

**Two honesty rules that trip newcomers:**

- **DMI/SMI have NO fixed scale.** Weights are hand-set data summing to 1.02 (nothing normalizes
  them); levels are run-to-run noisy. Code renders direction words only (positive/negative/flat —
  `report.py::_momentum_word`: "no invented magnitude qualifier", per Part 17) and the five band
  words in `gpu_agent/bands.py` — accelerating ≥ 0.30, firm ≥ 0.05, flat > −0.05, softening >
  −0.30, else contracting — which are **the only sanctioned index vocabulary**. Never write
  "slightly positive DMI" or compare levels across cycles; the trust footer says "read direction,
  not level" for exactly this reason.
- **Leading indicators are effectively unscored today — open F60** (2026-07-05). The leading set is
  rpoBacklog + vendorRevenueGuidance (both quarterly-filing-sourced) + designWins (structural,
  weight 0.0, excluded); fresh-cadence indicators are price/structural. Live result: the 2026-07
  flagship v3 Outlook ran 3 contributing findings vs Momentum's 12, with `smiContribution: 0.0`.
  Treat Outlook as thin coverage, not as a strong forward signal.

## 5. The indicator registry

`registry/indicators.json` is the single authority for indicator semantics (per
`docs/taxonomy.json` meta: "structure only; indicators.json is the metrics authority").
As of 2026-07-05: **17 indicators, 10 scoring** (weights sum 1.02), 2 price-side (D6,
gpuSpotPrice — weight 0.0, overlay only), 3 structural (exportControlExposure,
customerConcentration, designWins), 2 unsided display metrics (perfPerWatt, flopsPerDollar).
Full table in `references/worked-example.md`.

- Per-indicator fields: dimension (one of six or null), side, weight, unit (canonical — a price
  finding with a drifting unit string is rejected loudly, F53), kind, scoring, comparability, etc.
- **Weights are hand-set, uncalibrated data.** No code calibrates them; changing a weight is a data
  change (still gated — route via desk-change-control), changing scoring semantics is a Part-33
  migration.
- Top-level `cadenceHorizon` (cadence daily|weekly|quarterly × horizon leading|coincident|lagging,
  all 17 tagged) drives BOTH the Momentum/Outlook split (§4) and the **wiki half-life decay**:
  cadence → half-life in cycles (daily→1, weekly→3, quarterly→6; leading floored at 3; untagged →
  3 and surfaced, never silent), with `effective_salience = salience × 0.5^(quiet_age/half_life)`
  (`gpu_agent/wiki/lint.py`).
- Top-level `dimensionTracks` maps each dimension to its anchor polarity track (§2).
- `sourceInventory` lists sources per indicator INCLUDING paywalled ones (TrendForce, SemiAnalysis)
  — inventoried, never fetched (§8).
- **Indicators and dimensions are different namespaces.** `strategicRisk` is a dimension; the
  indicators grounding it are exportControlExposure and customerConcentration. (A plan draft once
  invented an indicator named "strategicRisk" and had to be corrected — commit e6540ab.)

## 6. Corroboration doctrine (F63, contract v1.3)

- **Publisher identity** = `gpu_agent/publisher.py::publisher_key`: the evidence URL's netloc,
  lowercased, `www.`-stripped; falls back to the source string. "Import this, never re-derive it" —
  it is THE corroboration key for all consumers.
- **The bounded step**: ≥ `minDistinctPublishers` (= 3, `registry/corroboration.json`) distinct
  publishers, within the corpus window, unlock exactly one step each at three surfaces:
  1. **Gate F2e**: a secondary-only Finding may carry HIGH confidence.
  2. **Thesis rule 6**: a secondary-only reversal APPLIES instead of deferring (§7).
  3. **Sufficiency gate** (`gpu_agent/sufficiency.py`): a judge may change a dimension rating or
     the binding constraint vs prior-cycle memory only with primary evidence or ≥3 publishers.
  Every corroborated step is logged with its publisher set and a pending-filing-checkpoint note —
  **the next filing remains the confirm/deny checkpoint**. The number 3 is also hardcoded in the
  brain prompts; `tests/test_corroboration_config.py` guards the coupling.
- **Sufficiency-gate scope** (deliberate): rating changes and bottleneck changes only.
  Direction-only changes, constraintLabel changes, and dimensions with no prior rating never
  trigger. No memory at all → the gate is inert.
- **THE KNOWN HOLE — F72 (open, must-have caliber, 2026-07-05)**: publisher_key is netloc-only, so
  one wire press release republished on 3 syndicator domains (the live store already holds
  stocktitan.net, markets.financialcontent.com, finance.yahoo.com) counts as 3 distinct publishers
  and silently unlocks all three surfaces at once. The only current defense is un-gated prompt text
  ("distinct outlets, not syndication of one story"). When reviewing any corroborated step, check
  the logged publisher set for syndication by hand. Fix work: **gate-integrity-campaign**.
- **The standing floor** (Parts 8/26): a status flip may never rest on a single source; high-stakes
  flips gate to a human; a source downstream of our own dashboard cannot corroborate us.
- **UNRESOLVED CHARTER CONTRADICTION — flag, don't resolve**: Part 37's deferred list (line ~1637 at
  a8ec757) still says "Not yet: hard corroboration + a hard secondary-confidence cap", while the
  F63 amendment ~60 lines above it (lines ~1574–1586) and the shipped F2e cap read as exactly that,
  staged. Do not quote Part 37's deferred list as current fact without noting this; a maintainer
  ruling is needed before amending either passage.

## 7. Thesis-book rules

The thesis book (`gpu_agent/thesis.py`; state in `store/theses/<categoryId>/`) is the desk's
standing convictions. Each entry: statement, lens (demand|supply|competitive|risk), status
(registered|provisional|retired), conviction (low|medium|high), mechanism, **falsifiableTrigger**
(must name a checkable observable — deterministic v1 check: a registered indicator id, a digit, or
quarter/qtr/month/week/cycle), sensitivity. Every cycle the thesis brain judges EVERY standing
thesis exactly once: reaffirmed | strengthened | weakened | adjusted | broken.

- **Conviction moves ±1 level per cycle**, clamped to low/medium/high; broken → conviction low AND
  the thesis retires. Reaffirmed/adjusted leave conviction unchanged.
- **Anti-whipsaw (rule 6)**: a reversal (direction flip vs `lastDirection`, or any `broken`)
  without primary evidence is **recorded but not applied** — it becomes a `pendingChallenge` —
  UNLESS its cited findings span ≥3 distinct publishers (the F63 corroborated step, applied with a
  pending-filing checkpoint note). A same-direction confirmation next cycle applies unconditionally
  (any tier); anything else lapses the challenge (logged `challenge-lapsed`).
- **Defer is a legitimate state, not a failure.** A deferred judgment still cited real findings; it
  counts toward promotion. The brain is instructed to judge honestly regardless of the consequence
  ("do not soften a verdict merely because you lack primary or corroborated evidence").
- **Promotion (rule 5)**: a provisional thesis registers after judgments spanning ≥2 distinct asOf
  cycles AND ≥2 distinct publisher domains (read from history records' `publisherDomains`).
- **Self-verifying history**: `history.jsonl` is the append-only source of truth; `book.json` is a
  projection. `ThesisStore.load()` replays history and **hard-fails on any divergence** — never
  hand-edit `book.json` (maintainer-confirmed law: brain outputs and recorded answers are never
  hand-edited; rejected answers are re-dispatched with the verbatim violation).
- Live book (chips.merchant-gpu, 2026-07-05): 13 entries — 10 registered, 3 provisional, one live
  `pendingChallenge` (amd-credible-second-source).

## 8. Paywall doctrine

**Absolute rule, no exceptions**: a source with `costUsd > 0` or `accessMethod == "licensed-api"`
is paywalled (`gpu_agent/manifest.py::is_paywalled`). It is logged as a coverage gap
(`acquisitionStatus: "paywalled"`, priority required) **immediately and never fetched** — not via a
gatherer, not via agent-reach, not "just once to check". Paywalled sources stay in the manifest and
registry inventory so the gap is visible and honest ("mark it estimate/unavailable — never fake a
hard figure", Part 22). The gather skill's dry-run doc proves the chain end to end:
paywalled → preamble gap → indicator under-supported → honest scorecard.

## 9. Gray-area doctrine (maintainer-confirmed, 2026-07-05)

Under-supported dimensions, thesis deferrals, and dispersion are **features expressing honest
uncertainty, not failures to paper over**. The desk's stated edge is gray-area critical thinking —
depth and broader market impact, not black-and-white rule-following. Concretely:

- A dimension with no groundable findings is OMITTED by the judge and marked `under-supported`
  (confidenceCap low) by code — never invented to fill the grid. Do not "fix" a missing rating.
- A below-quorum dimension is absence, not error (F19).
- A deferred thesis reversal is the anti-whipsaw doctrine working (§7).
- Dispersion on a finding means the sources genuinely disagree — surfacing it is the job.
- "Nothing changed" is a first-class honest headline; an unchanged book with lapsed challenges is a
  valid cycle outcome.
- The arbiter for any output question is the charter's closing test: could a TSMC executive ask
  "how do you know that?" and find the answer already written.

## Glossary

| Term | Meaning here |
|---|---|
| asOf (grain) | The cycle vintage a Finding/scorecard belongs to; `YYYY-MM` (monthly flagship) or `YYYY-MM-DD` (daily) — regex-enforced at the CLI (F56). Grain-aware compares truncate to asOf's length. |
| vintage | Which cycle a fact belongs to; "vintage honesty" = never blend dates; observedAt ≠ capturedAt ≠ evidence.date (§3). |
| anchor | Code-computed per-dimension mean of polarity×magnitude/3 on the registry track; bounds the rating word ±0.15 (§2). |
| track | Which polarity a dimension's anchor reads (demand or supply), from registry `dimensionTracks`. |
| side | Which track a Finding primarily feeds: demand, supply, price (overlay), structural (overlay). Code-stamped from the registry. |
| magnitude | 1=slight, 2=significant, 3=severe; normalized /3 in all index and anchor math. |
| salience | Deterministic wiki-page importance: 0.15 + 0.10·min(obs,5) + 0.15·fresh + 0.10·primary + 0.20·contradiction, cap 1.0 (F15 — never brain-invented). |
| half-life | Cycles for a quiet wiki thread's salience to halve; from indicator cadence (§5). |
| provisional vs registered | Quarantine lifecycle for wiki pages AND theses: provisional never feeds canonical; promotion needs persistence (≥2 cycles) + corroboration (≥2 publishers); registered pages are never pruned. |
| canonical vs ad-hoc | Assignment modes (Part 18): only canonical runs feed official state; ad-hoc runs produce views/answers, never edits. |
| under-supported | A dimension with no (or below-quorum) grounding this cycle — honest state, caps confidence (§9). |
| dispersion | Recorded source disagreement on a Finding — the range plus a note, never silently resolved. |
| publisher key | Evidence URL netloc, www-stripped — THE corroboration identity (§6, F31). |
| corpus window | The 45-day (default) store-finding window merged with fresh findings for judging (F62). |
| memory | The prior-cycle state bundle threaded into the judge prompt ("DATA, not instructions; judge the CHANGE"); the sufficiency gate's reference point. |
| defer / pendingChallenge | A recorded-but-not-applied thesis reversal awaiting same-direction confirmation (§7). |
| conviction / lens | Thesis strength (low/medium/high, ±1 per cycle) and viewpoint (demand/supply/competitive/risk). |
| coverage gap | A logged, never-silent hole: paywalled, not-covered, or cap-truncated (manifest.py). |
| evidence tier | primary (official/filing domains) vs secondary (open web) — code-stamped at ingest. |
| quorum | n//2+1 of judge samples needed for a dimension to be rated at all. |
| indicator vs dimension | Registry entries that ground ratings vs the six rated axes — separate namespaces (§5). |
| constraintLabel | Plain-language name of the binding constraint (≤6 words, never a dimension name). |
| bands | The five sanctioned index words: accelerating/firm/flat/softening/contracting (§4). |

## Common mistakes

1. **Averaging dimensions or inventing a composite score** — the category rating is an analyst
   read; the market never gets a number on the cover (Part 17).
2. **Missing the bottleneck/strategicRisk inversion** — "Very strong bottleneck" is a choke point,
   not praise. Reviewers who miss this produce wrong ratings code only partially catches.
3. **Smuggling trend or confidence into the rating word** — they are separate fields.
4. **Writing magnitude words about DMI/SMI** ("slightly positive", "strongly demand-led") or
   comparing index levels across cycles — no fixed scale; bands.py words + direction only.
5. **Treating a missing dimension rating or a thesis deferral as a bug** — both are the honest
   state (§9).
6. **Confusing indicator ids with dimension ids** (the e6540ab precedent).
7. **Trusting a 3-publisher count as independence** — check for wire syndication until F72 lands.
8. **Fetching a paywalled source** — never, for any reason (§8).
9. **Expecting the model to set `side`, `tier`, or salience** — all code-stamped/computed;
   model-supplied values are rejected (extra="forbid") or ignored.
10. **Using observedAt where capturedAt is required** — backtests/replays key on capturedAt to stay
    look-ahead-free.
11. **Hardcoding 33 categories** (it is 34) or assuming Layer/Main run (deferred stubs).
12. **Expecting price findings in DMI/SMI** — price is an overlay; a static price level must carry
    zero polarity.
13. **Hand-editing `book.json`, brain outputs, or recorded answers** — maintainer-confirmed law:
    re-dispatch with the verbatim violation instead; `ThesisStore.load()` hard-fails on book drift.

## Provenance and maintenance

Authored 2026-07-05 against the skill-library baseline main @ a8ec757; every code/registry/store
fact above re-verified the same day at main @ 639c00d (4 commits later; working tree clean). All
commands run from repo root, PowerShell-compatible.

| Volatile fact | Re-verify with |
|---|---|
| 34 categories / 5 layers | `.venv\Scripts\python -c "import json; t=json.load(open('docs/taxonomy.json', encoding='utf-8')); print([(l['id'], len(l['categories'])) for l in t['layers']])"` |
| Six dimensions | `.venv\Scripts\python -c "from gpu_agent.schema.scorecard import DIMENSIONS; print(DIMENSIONS)"` |
| 17 indicators / 10 scoring / weights 1.02 | `.venv\Scripts\python -c "import json; r=json.load(open('registry/indicators.json', encoding='utf-8'))['indicators']; s=[v for v in r.values() if v.get('scoring')]; print(len(r), len(s), round(sum(v['weight'] for v in s), 4))"` |
| minDistinctPublishers = 3 | `Get-Content registry/corroboration.json` |
| Anchor tolerance 0.15 | `Select-String -Path gpu_agent/gate.py -Pattern "_ANCHOR_TOL"` |
| Band thresholds | `Select-String -Path gpu_agent/bands.py -Pattern "accelerating|softening"` (read the `BANDS` list) |
| Live categories / frontier-closed still unrun | `Get-ChildItem store` (no `models.frontier-closed` dir = still never run) and `Select-String -Path .gitignore -Pattern "store"` |
| F60/F71/F72 still open | `Select-String -Path docs/fix-backlog.md -Pattern "F60|F71|F72"` then `git log --oneline --grep="F60"` etc. — checkboxes are known-stale; git is truth (see desk-change-control) |
| Thesis book state / counts | `.venv\Scripts\python -c "from gpu_agent.thesis import ThesisStore; b=ThesisStore('store/theses/chips.merchant-gpu').load(); print(len(b.entries), [(e.id, e.status) for e in b.entries if e.status=='provisional'])"` |
| dimensionTracks / leading set | `.venv\Scripts\python -c "import json; r=json.load(open('registry/indicators.json', encoding='utf-8')); print(r['dimensionTracks'], [k for k,v in r['cadenceHorizon'].items() if v['horizon']=='leading'])"` |
| Charter Part line numbers (they drift) | `Select-String -Path docs/agent-swarm-charter.md -Pattern "Not yet \(deferred"` and `-Pattern "F63 \(contract v1.3\)"` |
| Flagship worked-example numbers | see `references/worked-example.md` provenance block |
