# Product decisions & action items

> Running log of product-shaping decisions from spec Q&A, and the standing action items they
> created. The question here is always **what the output should be** — not how it is built.

## Action Item 1 — The Depth Bar + Golden Set (open, highest priority)

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
