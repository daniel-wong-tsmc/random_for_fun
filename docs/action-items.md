# Product decisions & action items

> Running log of product-shaping decisions from spec Q&A, and the standing action items they
> created. The question here is always **what the output should be** — not how it is built.

## Action Item 1 — The Depth Bar + Golden Set (superseded-in-part 2026-07-04; episode half open)

**Problem (two halves, one workstream):**
1. LLM analysis defaults to surface level — ten balanced considerations, no position, nothing
   falsifiable — which is exactly why humans can't agree on it: there is nothing to grab onto.
2. The project has no golden dataset — no examples of what a *correct, deep* output looks like,
   so agent quality cannot be graded or regression-tested.

**Resolution — combine them:** depth can't be enforced without a grading standard, and a grading
standard needs resolved cases. History supplies resolved cases for free.

**Half 1 — the Depth Rubric.** "Deep enough" defined as checkable properties, gradeable by a
human or an LLM judge:
1. **Crux identification** — names the 1–2 questions that actually decide the conclusion.
2. **Mechanism, not narrative** — explicit causal chain, each link separately evidenced.
3. **Sensitivity** — states which assumption, if wrong by ~2x, flips the conclusion.
4. **Steelmanned counter-case** — strongest objection stated and answered, as a shipping gate.
5. **Differentiation vs. consensus** — what the market already believes, and where/why this departs.
6. **Falsifiable triggers** — the conclusion implies observables.

The point is not analysis everyone agrees *with* — it is analysis where disagreement is
**localizable** ("I dispute Finding #12's link"), so it can be adjudicated with evidence instead
of just felt.

**Half 2 — the Golden Set (backtesting).** Pick 5–10 resolved episodes from 2023–2026 (candidates:
DeepSeek moment, CoWoS crunch, Ethernet-overtakes-InfiniBand, nuclear PPA wave, HBM tightness,
app-layer GRR froth). For each: freeze an information cutoff T, allow only pre-T sources, run the
desk as-of T, grade the output on (a) crux found, (b) how the recommendation aged, (c) Depth Rubric
score, (d) comparison vs. the best contemporaneous human analysis (the bar to beat). These become
permanent regression tests for every agent change.

**Known caveat:** backtests flatter LLMs (training data knows what happened after T). Mitigations:
pin sources pre-T, grade the reasoning chain over the verdict, rubric score primary / directional
correctness secondary.

**Definition of done:** a written Depth Rubric + a golden set of episode briefs (input cutoff,
expected crux, expected call, grading notes) that the first Category Agent is developed *against*.

**Status (2026-07-04, user-approved):** superseded-in-part. Half 1 shipped: the depth fields
(mechanism / falsifiableTrigger / sensitivity) are gate-enforced and the F6 rubric grades them.
The regression-gating goal shipped as F6's 18-case golden set + the armed hash-pin gate — but
that set is live-cycle-derived, not episode-derived. Half 2 (episode backtests) remains open
and sits in roadmap Phase 7; the desk-maturity analog library assembles the same episode set,
and 1–2 episodes become frozen eval cases when it lands. The original "developed against"
definition of done was not met — recorded here, not quietly dropped.

## Decisions recorded (2026-07)

- **Reader:** a real TSMC executive — not "executive-grade" as a mere quality bar.
- **Recommendation altitude:** aggregate all layers into an *extremely educated next step*, fully
  transparent about why and how it was reached. Not option-framing only, not unexplained verdicts.
- **Recommendations are a spectrum (position book):** "nothing changed" is an honest, legitimate
  cycle output — but near-zero change is still change. Standing recommendations are maintained
  like a position book: each cycle every position is re-affirmed / strengthened / weakened /
  adjusted with an explicit delta, rather than binary new-call vs. no-call.
- **Horizons are per-domain (clock speeds):** near-term is valued on par with long-term, but the
  meaning of "near-term" differs by domain — fab-related decisions: <6 months matters; model-layer
  trends: <1 month matters. Recommendations carry domain-appropriate horizons and review dates,
  not one global cadence.
- **Machinery visibility:** everything trackable always; nothing needs to be shown up front. The
  UI must allow full deep-dive later (calibration, noise-discard lists, evidence chains behind
  drill-down).
- **Cover layout:** (a) stacked above (b) — a quick market read (status + binding bottleneck +
  top recommendation) on top, the full 5-layer cake with per-layer ratings underneath.

## Verdict — blind baseline ablation 2026-07 (user-scored 2026-07-06)

**Question:** does the desk beat cheap baselines? **Setup:** `docs/ablation-2026-07/` — three
artifacts on the same scope (merchant GPU market state, ~45 days, as of 2026-07-05), blind,
random A/B/C: A = RSS-digest baseline (one web-only subagent), B = the desk (2026-07 flagship
render + 2026-07-05 daily render), C = one-shot deep-research baseline (one web-only subagent).
The user read blind and judged without the rubric; verbatim substance of the verdict:

- **A (RSS digest):** "tells me a lot but doesn't tell me what to look out for / the
  implications. It is just a bunch of news articles that are put together"; many items old and
  not relevant.
- **B (the desk):** "I quite like every single section that [is] there because it tells me the
  implications and what to look out for." Criticisms: "topics and sections are very scattered
  and all over the place"; "way too much information so we would need to order by importance
  and adjust format."
- **C (deep-research):** organized and easier to digest, names risks/constraint/demand-supply,
  but much of the information is old and "I can't really take this information back to my desk
  and start working on a particular aspect."

**Read:** the desk won the blind comparison on substance — implications and watch items are
exactly the thesis-book/trigger machinery, and neither baseline produced them. Every desk
deficit named is presentation-layer: section ordering, importance ranking, volume control.
The baselines' shared failure (stale, non-actionable) also validates the freshness lanes
(F57/F58) and the actionability direction (F64 trigger-first brief, F65 "So what for TSMC").

**Actions:** presentation fixes logged as **F77** in `docs/fix-backlog.md` (order the brief by
importance, consolidate scattered sections, cap volume); F64/F65 remain the actionability
vehicles. The desk's intelligence layer is validated; the next investment frontier is the
render, not the gathering or judging machinery.

## Open — decision-area expansion (proposed, awaiting confirmation)

Current four (capacity/capex, pricing, accounts, risk) are "how much and for whom." Proposed adds
("what and where"):
- **Technology roadmap** — which capabilities to build: CoWoS-L vs. SoIC mix, glass substrates,
  co-packaged optics, HBM4 base dies, A16/backside power.
- **Geographic footprint & siting** — AZ/JP/DE pacing off geopolitics + customer pull + energy
  availability (gives Layer 1 a first-class TSMC linkage via time-to-power).
- **Ecosystem & partnerships** — OSAT overflow (ASE/Amkor), standards posture (UCIe, UEC, HBM),
  co-development, supplier co-investment.

Cap at seven total; upstream supply-chain security folds into **risk** rather than becoming an
eighth area.
