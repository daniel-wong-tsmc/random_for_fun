# F24 stage 2 — Entity registrations for the v2.0 era + historical page consolidation

**Status:** approved design, ready for a lane plan.
**Decision provenance — user-approved 2026-07-13 (interactive, orchestrator session):**
(1) historical split-page consolidation = **scripted merge + full diff, NOTHING commits until
the user signs** (the F80 pattern at larger scale); (2) entity registration set = the
F79-aligned full set (assistant lean stated in the wave design and accepted with it; the user
may trim at the diff review). Unsettled forks = QUESTION-STOP →
`.superpowers/handoffs/f24-stage2-QUESTIONS.md`, end turn, wait.

## Part A — register the entities the six new F79 series cite (data only, lands FIRST)

Extend `docs/taxonomy.json` `seedEntities` (the home F24 stage 1 standardized on) with
id/name/aliases/appearsIn/primaryCategory for: **amd, intel, broadcom** (merchant lane —
primaryCategory chips.merchant-gpu); **microsoft, alphabet, amazon, meta, oracle**
(hyperscaler buyers — primaryCategory infrastructure.hyperscale-cloud, appearsIn
chips.merchant-gpu); **sk-hynix, samsung, micron** (memory — primaryCategory chips.hbm-memory,
appearsIn merchant-gpu); **hon-hai (alias Foxconn), quanta, wistron, wiwynn, supermicro
(alias SMCI)** (ODMs — appearsIn merchant-gpu; primaryCategory per taxonomy's best-fit
infrastructure category — if none fits honestly, QUESTION-STOP rather than force one);
**coreweave, lambda-labs** (neoclouds — primaryCategory infrastructure.neocloud, appearsIn
merchant-gpu). nvidia and tsmc already exist. Aliases must cover tickers and common press
forms (e.g. NVDA-style tickers, "Hon Hai Precision", "Google"). Lane discipline: merchant-gpu
OWNS only merchant vendors; everything else is appearsIn (charter Part 21).
**Constraint proven by stage 1: zero emitted-prompt bytes change** (the resolver is code-side;
the F6 pin must stay green) — if any registration somehow reaches a prompt, QUESTION-STOP.
Extend `tests/test_entities.py` alias coverage per entity. **F79's lane consumes these ids —
this part lands as the lane's first pushed commit so F79 can reference them.**

## Part B — the nvda→nvidia historical consolidation (script + user-signed diff)

A deterministic, replayable one-shot script (new, e.g. `gpu_agent/tools/consolidate_entity.py`
or `scripts/`): merges `store/wiki/entity/nvda.md` history into the canonical
`entity:nvidia` page as APPEND-ONLY wiki-log events (provenance-labeled `consolidation`
events; nothing rewritten, the log stays append-only), produces the merged page state, marks
the old page retired/archived with a pointer note (so lint/corpus stop double-counting without
special-casing forever), and emits a FULL before/after diff artifact + a summary (events
moved, salience/state resolution rule applied). **The lane commits the SCRIPT + its tests
only. Running it against the live store and committing the result is a USER-SIGNED step:**
the lane runs it in a scratch copy, writes the diff to its sentinel/QUESTIONS file, and STOPS
for sign-off — the orchestrator relays; only after the user signs does the store edit commit
(same ceremony as F80). Salience/state conflicts between the two pages resolve by
latest-vintage-wins with the losing value preserved in the consolidation event body; if the
pages carry CONTRADICTORY states the rule cannot order, QUESTION-STOP with both shown.
Check `taiwan-semiconductor` vs `tsmc` for the same split shape while there; include it in
the diff if found.

## Lane ownership / hard constraints

Owns: `docs/taxonomy.json` seedEntities, `tests/test_entities.py` extensions, the
consolidation script + its tests (script tested against synthetic fixtures, never the live
store in tests). Must NOT touch: `store/` (except via the user-signed Part-B run),
`gpu_agent/wiki/` internals (use existing store APIs), prompts, frozen core, F79's files
(`scoring.py`, `indicators.json`, `change.py`), F65's files. Suite green at every commit
(baseline 1346/5); F6 pin green throughout.

## Acceptance

1. Every listed entity resolves (all alias forms → canonical id) with tests.
2. F6 pin green after Part A (zero prompt bytes).
3. Script: synthetic-fixture tests cover merge, retire-pointer, conflict rule, and idempotence
   (running twice changes nothing the second time).
4. The live-store diff artifact produced and parked for user sign-off (NOT committed).
5. Full suite green.

## Non-goals

Editing the live store without the signature; wiki internals changes; new categories in the
taxonomy (structural changes take the Part 16 human gate — registrations of existing-category
entities do not); F79's registry/indicators.json.
