# Charter compliance matrix (F23)

> Maps every **binding** clause of `docs/agent-swarm-charter.md` to where it is actually enforced and
> the test that pins it. **Honesty is the product** — an accurate `NOT-ENFORCED` row is a success, not
> a failure. This exists to stop "binding" from drifting into aspiration, the way F2, F3, and F5 did.
> Design: `docs/superpowers/specs/2026-07-12-f23-compliance-matrix-design.md`.
>
> **Format contract (kept parseable by `tests/test_compliance_matrix.py`):** the matrix is the single
> 6-column table under "Compliance matrix"; the summary is the single `Status | Count` table under
> "Summary". Every data row has exactly 6 cells and no literal pipe inside a cell. Paths are
> repo-root-relative and must exist; a `path::name` reference must name a real function. **No line
> numbers** anywhere — reference a function or rule by name in parentheses (line numbers rot on every
> edit). `Status` is exactly one of:
> `ENFORCED · PARTIAL · SESSION-PROSE · DEFERRED · NOT-ENFORCED · NARRATIVE`.
>
> **Status meanings:**
> - `ENFORCED` — a deterministic code path (gate / lint / schema / scoring) enforces it, with a pinning test.
> - `PARTIAL` — enforced, but the charter itself flags the enforcement as staged / conservative / scoped
>   relative to the full binding intent, or enforced in code without a dedicated pinning test.
> - `SESSION-PROSE` — enforced only by skill / prompt prose an agent follows at run time; no deterministic pin.
> - `DEFERRED` — a binding mechanism the charter or roadmap explicitly defers to a later phase.
> - `NOT-ENFORCED` — reads as in-force but nothing enforces it. The aspiration-drift this matrix exists to catch.
> - `NARRATIVE` — descriptive context; states no independently-enforceable rule.

## Summary

| Status | Count |
|---|---|
| ENFORCED | 57 |
| PARTIAL | 25 |
| SESSION-PROSE | 10 |
| DEFERRED | 26 |
| NOT-ENFORCED | 3 |
| NARRATIVE | 0 |

Read this as: the in-force **explainability doctrine** (Parts 1, 2, 7, 8, 17) is genuinely enforced in
code — the drift that produced F2 / F3 / F5 has been closed. The large `DEFERRED` block is the
productionization and Layer / Main tiers the charter itself marks "Not yet." The three `NOT-ENFORCED`
rows and the thinner `PARTIAL` rows are the honest gaps — see Findings.

## Compliance matrix

| Clause ID | Part | Clause | Status | Enforcement | Pinning test |
|---|---|---|---|---|---|
| P1.1 | 1 | Every metric has a why; no naked numbers | ENFORCED | gpu_agent/gate.py (check_finding, why non-empty) | tests/test_gate_finding.py::test_empty_why_fails |
| P1.2 | 1 | Never fabricate a number; non-measured value must be null | ENFORCED | gpu_agent/gate.py (check_finding, invented-value check) | tests/test_gate_finding.py::test_observed_with_value_is_invented_number |
| P1.3 | 1 | State the impact (targets, direction, mechanism) | ENFORCED | gpu_agent/gate.py (F21 targets and mechanism non-empty) | tests/test_gate_finding.py |
| P1.4 | 1 | Explain the causal why, not just the what | PARTIAL | gpu_agent/gate.py (why non-empty only) plus gpu_agent/evals/rubric.py (causal quality judged) | tests/test_evals_rubric.py |
| P1.5 | 1 | Always state the source (name, url, date); primary over secondary | ENFORCED | gpu_agent/gate.py (F2a evidence required, ISO date) plus gpu_agent/gathering/ingest.py (tier stamped) | tests/test_gate_finding.py |
| P1.6 | 1 | Label hypotheses; cap confidence; show reasoning | ENFORCED | gpu_agent/gate.py (hypothesis reasoning plus confidence cap) | tests/test_gate_finding.py |
| P1.7 | 1 | Write for a human; plain language, lead with the answer | PARTIAL | gpu_agent/judgment/judge.py (voice lint) plus SESSION-PROSE (skill: stop-slop) | tests/test_judge_voice_lint.py |
| P1.q1 | 1 | Confidence always present with a stated basis | ENFORCED | gpu_agent/schema/finding.py (confidence required) | tests/test_finding_schema.py |
| P1.q2 | 1 | Dispersion when sources disagree; never silently pick one | ENFORCED | gpu_agent/gathering/dedup.py (conflicting keys set dispersion) | tests/test_dedup_classify.py |
| P2.measured | 2 | measured: value required plus at least one dated source | ENFORCED | gpu_agent/gate.py (check_finding kind rules) | tests/test_gate_finding.py::test_measured_without_value_fails |
| P2.observed | 2 | observed: value must be null, evidence required | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py |
| P2.hypothesis | 2 | hypothesis: value null, reasoning required, confidence at most medium | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py |
| P2.polarity | 2 | v1.1 demand/supply read: side set plus at least one non-zero polarity | ENFORCED | gpu_agent/gate.py (affects-neither-track check) | tests/test_gate_finding.py |
| P2.schema | 2 | The Finding is the frozen atomic unit, schema-validated | ENFORCED | gpu_agent/schema/finding.py | tests/test_finding_schema.py |
| P3.scorecard | 3 | Scorecard = findings plus six dimension ratings that name their finding IDs | ENFORCED | gpu_agent/schema/scorecard.py plus gpu_agent/gate.py (ratings cite finding IDs) | tests/test_scorecard_schema.py |
| P3.tiers | 3 | Three tiers Category, Layer, Main; v1 builds Category only | DEFERRED | DEFERRED (Layer and Main - roadmap Phases 3 and 5; charter Part 38 Not yet) | — |
| P4.memory | 4 | Each tier reads prior state plus notebook and interrogates the change | ENFORCED | gpu_agent/memory.py (prior-state bundle into judge and thesis prompt) | tests/test_memory_bundle.py |
| P4.series | 4 | State time-series persisted so compare-to-before is a query | ENFORCED | gpu_agent/store.py plus gpu_agent/wiki/store.py | tests/test_store.py |
| P5.chassis | 5 | Structured outputs plus pre-commit schema validation; read-prior write-snapshot | ENFORCED | gpu_agent/schema/finding.py plus gpu_agent/gate.py plus gpu_agent/store.py | tests/test_finding_schema.py |
| P5.delegation | 5 | Delegation one level deep; agents reason, code computes | SESSION-PROSE | SESSION-PROSE (.claude/skills/gather-category/SKILL.md, .claude/skills/run-cycle/SKILL.md) | — |
| P5.tiers2 | 5 | Layer and Main are memory-backed, no web; rollups computed in code | DEFERRED | DEFERRED (Layer and Main deferred - charter Part 38) | — |
| P6.frozen | 6 | Output schema frozen at each boundary; the next tier's only input | ENFORCED | gpu_agent/schema/finding.py plus gpu_agent/schema/scorecard.py | tests/test_finding_schema.py |
| P6.rollup | 6 | Code-computed DMI, SMI, SDGI travel up the contract | ENFORCED | gpu_agent/scoring.py | tests/test_scoring.py |
| P7.a | 7 | Every measured Finding has a value and at least one dated source | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py |
| P7.b | 7 | No observed or hypothesis Finding carries an invented value | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py |
| P7.c | 7 | Every Finding has a non-empty why | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py::test_empty_why_fails |
| P7.d | 7 | Every Finding has an impact (targets, direction, mechanism) | ENFORCED | gpu_agent/gate.py (F21) | tests/test_gate_finding.py |
| P7.e | 7 | Provenance (evidence) or, for a hypothesis, reasoning | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py |
| P7.f | 7 | Every hypothesis labeled and capped at confidence medium | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py |
| P7.g | 7 | Conflicting sources surfaced as dispersion, not silently resolved | ENFORCED | gpu_agent/gathering/dedup.py | tests/test_dedup_classify.py |
| P7.h | 7 | Every rating, stance, or status names the Finding IDs that justify it | ENFORCED | gpu_agent/gate.py (check_scorecard citations) | tests/test_gate_scorecard.py |
| P7.i | 7 | No Finding cites the dashboard's own prior output (no self-reference) | ENFORCED | gpu_agent/gate.py (check_scorecard self-reference) | tests/test_gate_scorecard.py |
| P7.j | 7 | Every canonical Finding declares its demand/supply polarity | ENFORCED | gpu_agent/gate.py (affects-neither-track check) | tests/test_gate_finding.py |
| P7.k | 7 | No dimension rating contradicts its cited measured anchor | ENFORCED | gpu_agent/gate.py (F36 rating-consistent-with-anchor) | tests/test_gate_scorecard.py |
| P8.orphan | 8 | No orphan numbers, no invented numbers (the two cardinal sins) | ENFORCED | gpu_agent/gate.py (check_finding) | tests/test_gate_finding.py::test_measured_without_value_fails |
| P8.injection | 8 | Fetched content is data, not instructions | PARTIAL | gpu_agent/extraction/prompt.py (F16 delimiting) plus SESSION-PROSE (tool-less dispatch, .claude/skills/gather-category/SKILL.md) | tests/test_extraction_prompt.py |
| P8.primary | 8 | Primary over secondary; mark the tier; let confidence reflect it | ENFORCED | gpu_agent/gathering/ingest.py (tier stamp) plus gpu_agent/gate.py (F2e cap) | tests/test_gate_corroboration.py |
| P8.dispersion | 8 | Report dispersion; when the world disagrees the range is the finding | ENFORCED | gpu_agent/gathering/dedup.py | tests/test_dedup_classify.py |
| P8.vintage | 8 | Vintage honesty: asOf per Finding; no future-dated evidence; no blended dates | ENFORCED | gpu_agent/gate.py (F17 future-dated and ISO checks) | tests/test_gate_finding.py |
| P8.accountability | 8 | Revisit prior calls each cycle; keep confidence calibrated | PARTIAL | gpu_agent/thesis.py (apply engine revisits calls); Brier calibration deferred | tests/test_thesis_apply.py |
| P8.humanloop | 8 | Human-in-the-loop on high-stakes flags before flipping the headline | DEFERRED | DEFERRED (no Main tier or headline flip in v1 - charter Part 23 and 38) | — |
| P9.append | 9 | Canonical store is an append-only versioned time-series | PARTIAL | gpu_agent/store.py plus gpu_agent/wiki/store.py (JsonStore now; canonical SQLite store deferred) | tests/test_store.py |
| P9.scoped | 9 | A scoped query tool enforces the read topology (sibling isolation) | DEFERRED | DEFERRED (scoped query tool - charter Part 38 Not yet) | — |
| P9.adjacent | 9 | Layer reads adjacent-layer summaries only, prior cycle, never raw | DEFERRED | DEFERRED (Layer tier deferred - roadmap Phase 3) | — |
| P10.rec | 10 | Recommendation record; no naked recommendation; traceable to Findings | DEFERRED | DEFERRED (Recommendation skill is Layer and Main - roadmap Phases 3 and 5) | — |
| P10.triage | 10 | Signal-vs-noise triage; show the filter; anti-whipsaw stability | PARTIAL | gpu_agent/thesis.py (F5 anti-whipsaw apply engine); full recommendation triage deferred | tests/test_thesis_apply.py |
| P10.laneown | 10 | Category surfaces signals plus a one-line implication; it does not recommend | SESSION-PROSE | SESSION-PROSE (roadmap Lane discipline; .claude/skills/run-cycle/SKILL.md) | — |
| P11.skill | 11 | The recommendation Skill is loaded by Layer and Main, never Category | DEFERRED | DEFERRED (roadmap Phases 3 and 5) | — |
| P12.calib | 12 | Log predictions, resolve on maturity, score calibration (Brier) | DEFERRED | DEFERRED (F64 Brier - roadmap Phase 1, not built) | — |
| P12.honesty | 12 | When a prior call was wrong, say so explicitly and update the thesis | PARTIAL | gpu_agent/thesis.py (applied broken retires; pending-challenge on reversal) | tests/test_thesis_apply.py |
| P13.caps | 13 | A capability gap flags the agent under-supported and confidence-caps it | PARTIAL | gpu_agent/manifest.py (coverage manifest, under-supported flag) | tests/test_manifest.py |
| P13.undersupported | 13 | A recommendation missing a required capability is flagged under-supported | DEFERRED | DEFERRED (recommendation layer deferred) | — |
| P14.ondemand | 14 | On-demand desk; answer from the store first, research only the gaps | DEFERRED | DEFERRED (interactive path - charter Part 38 Not yet) | — |
| P15.macro | 15 | Exogenous overlay tracked as Findings; owned by Main | DEFERRED | DEFERRED (Main tier deferred; macro overlay not built) | — |
| P16.declarative | 16 | A new category is a taxonomy entry plus archetype plus approval, no code fork | ENFORCED | docs/taxonomy.json plus gpu_agent/registry/structure.py plus gpu_agent/assignment.py | tests/test_taxonomy_scope.py |
| P16.humangate | 16 | Structural taxonomy changes (add, retire, merge) need human approval | SESSION-PROSE | SESSION-PROSE (governance; no code gate) | — |
| P16.version | 16 | Taxonomy version bumped so every prior snapshot stays reproducible | PARTIAL | docs/taxonomy.json (version field); the bump itself is not test-pinned | — |
| P17.split | 17 | Measured facts and judgments kept apart; never invent a score | ENFORCED | gpu_agent/gate.py plus gpu_agent/scoring.py (no synthetic 0-100) | tests/test_scoring.py |
| P17.scale | 17 | Five-word rating scale with written, repeatable definitions | ENFORCED | gpu_agent/bands.py plus docs/rating-anchors.md | tests/test_rating_anchors.py |
| P17.weakest | 17 | Category is an analyst read not an average; layer is its weakest link | PARTIAL | gpu_agent/bands.py (category overall); layer weakest-link deferred with Layer tier | tests/test_bands.py |
| P17.dualtrack | 17 | DMI, SMI, SDGI computed in code from polarity; price and structural excluded | ENFORCED | gpu_agent/scoring.py (F8 price overlay) | tests/test_scoring.py::test_strategic_risk_findings_excluded_from_dmi_smi |
| P17.anchor | 17 | The measured anchor bounds the rating (bias guardrail), never sets it | ENFORCED | gpu_agent/gate.py (F36) | tests/test_gate_scorecard.py |
| P17.plain | 17 | Plain-language rule (binding): readable without a glossary | PARTIAL | gpu_agent/judgment/judge.py (voice lint) plus gpu_agent/dashboard/plain_language.py plus SESSION-PROSE (skill: stop-slop) | tests/test_judge_voice_lint.py |
| P18.contract | 18 | Small sacred fixed contract (6 dims, schema, scale, rollup); not overridable | ENFORCED | gpu_agent/schema/finding.py plus gpu_agent/schema/scorecard.py plus gpu_agent/scoring.py | tests/test_scorecard_schema.py |
| P18.defineonce | 18 | Define each thing once, refer by id (three registries) | ENFORCED | registry/indicators.json plus gpu_agent/registry/structure.py plus docs/taxonomy.json | tests/test_registry_structure.py |
| P18.template | 18 | One template, many instances (assignment-driven scope) | ENFORCED | gpu_agent/assignment.py | tests/test_assignment_category.py |
| P18.provisional | 18 | Provisional never feeds canonical (quarantine until promoted) | PARTIAL | gpu_agent/wiki/lifecycle.py (provisional and registered status) | tests/test_lifecycle_prune_quarantine.py |
| P18.canonical | 18 | Canonical vs ad-hoc: ad-hoc runs never write the official state | SESSION-PROSE | SESSION-PROSE (mode on the assignment; .claude/skills/run-cycle/SKILL.md) | — |
| P18.modularity | 18 | Modularity binding: every component behind a named seam or registry | ENFORCED | gpu_agent/llm/factory.py plus gpu_agent/cycle.py plus registry/web-reach-tools.json | tests/test_llm_backends.py |
| P18.version | 18 | Version everything, stamp it on every output | PARTIAL | gpu_agent/schema/finding.py (schemaVersion) plus gpu_agent/schema/scorecard.py (provenance) | tests/test_finding_schema.py |
| P19.nosilent | 19 | Never a silent partial; the run states what was run vs skipped | ENFORCED | gpu_agent/cycle.py (cycle log: run vs skipped and why) | tests/test_store_cycle_log_integrity.py |
| P19.publish | 19 | Publish rule (quorum plus staleness); a failed binding category forces a hold | DEFERRED | DEFERRED (Main publish rule - Layer and Main deferred) | — |
| P19.grader | 19 | Grader-iteration cap; ship best-effort flagged, never loop forever | SESSION-PROSE | SESSION-PROSE (.claude/skills/gather-category/SKILL.md, .claude/skills/run-eval/SKILL.md) | — |
| P20.stamp | 20 | A provenance stamp on every Finding (modelId, promptVersion, versions, runId) | PARTIAL | gpu_agent/schema/scorecard.py (provenance) plus gpu_agent/pipeline.py (assignment@version only) | tests/test_scorecard_schema.py |
| P20.snapshot | 20 | Source snapshots captured plus content-hashed so citations survive link rot | ENFORCED | gpu_agent/schema/raw_document.py plus gpu_agent/gathering/ingest.py (content hash) | tests/test_raw_document.py |
| P20.replay | 20 | Reproducible: re-running on the pinned inputs yields an equivalent result | ENFORCED | gpu_agent/llm/recorded.py | tests/test_replay_v12.py |
| P21.countonce | 21 | A multi-category entity is counted once, owned by its primaryCategory | DEFERRED | DEFERRED (reconciliation runs at Layer and Main - deferred) | — |
| P21.resolve | 21 | Alias dedup (NVDA, nvidia) plus per-category entity namespacing before counting | NOT-ENFORCED | NOT ENFORCED - aspiration (F24 open: no entity registry, no alias canonicalization, entity id is global) | — |
| P22.tiered | 22 | Tiered acquisition; an unsourceable metric is estimate or unavailable, never faked | PARTIAL | gpu_agent/gathering/ingest.py (tier stamp) plus gpu_agent/gate.py (secondary cap) | tests/test_ingest.py |
| P22.allowlist | 22 | A license and ToS allowlist enforced by the fetch tool | SESSION-PROSE | SESSION-PROSE (paywall boundary followed by gatherers; no code allowlist) | — |
| P22.tables | 22 | Structured tables extracted by code, not the model's eyes | PARTIAL | gpu_agent/pricefeed.py (code-extracted price data); general PDF and Excel extraction not built | tests/test_pricefeed_helpers.py |
| P23.humanloop | 23 | Human-in-the-loop made operational: trigger, approver, SLA, pending state | DEFERRED | DEFERRED (charter Part 38 Not yet; no Main or headline in v1) | — |
| P23.access | 23 | Role-based human access and a data classification | NOT-ENFORCED | NOT ENFORCED - aspiration (no access control or classification in v1) | — |
| P24.golden | 24 | A frozen human-curated golden set per archetype with a rubric | ENFORCED | gpu_agent/evals/cases.py plus gpu_agent/evals/harness.py | tests/test_evals_cases.py |
| P24.gate | 24 | Prompt regression gate: no promptVersion reaches canonical below the incumbent | ENFORCED | gpu_agent/evals/prompt_hash.py plus gpu_agent/evals/harness.py | tests/test_evals_baseline_pin.py |
| P24.gradethegrader | 24 | Grade the grader: track its agreement with humans, re-tune drift | SESSION-PROSE | SESSION-PROSE (.claude/skills/run-eval/SKILL.md; periodic manual) | — |
| P24.stability | 24 | Run-to-run consistency sampled; instability alerted, not shipped | PARTIAL | gpu_agent/evals/harness.py (replicate runs, epsilon tolerance) | tests/test_evals_v2.py |
| P24.backtest | 24 | A backtest harness replays past dates look-ahead-free | DEFERRED | DEFERRED (backtest harness - roadmap continuous track, not built) | — |
| P25.qualify | 25 | A new model or prompt clears the golden set before it may run canonical | ENFORCED | gpu_agent/evals/prompt_hash.py (hash pin blocks canonical) | tests/test_evals_baseline_pin.py |
| P25.shadow | 25 | Shadow runs: candidate compared to incumbent on live inputs before promotion | SESSION-PROSE | SESSION-PROSE (migration shadow-runs; docs/migrations/2026-07-contract-v1.2.md) | — |
| P25.rebaseline | 25 | Calibration re-baselined and segmented by modelId on a brain swap | DEFERRED | DEFERRED (calibration Part 12 deferred) | — |
| P26.privsep | 26 | Privilege separation at fetch; content can populate evidence, never emit tool calls | SESSION-PROSE | SESSION-PROSE (tool-less gatherer dispatch; .claude/skills/gather-category/SKILL.md) | — |
| P26.corroboration | 26 | Primary-over-secondary as a hard corroboration bar for market-moving Findings | PARTIAL | gpu_agent/gate.py (F2e) plus gpu_agent/sufficiency.py plus gpu_agent/publisher.py; staged, not full | tests/test_sufficiency.py |
| P26.circular | 26 | Circular-source detection: a source downstream of us cannot corroborate us | PARTIAL | gpu_agent/gate.py (self-reference) plus registry/syndicators.json (exact-hash collapse); near-dup deferred | tests/test_publisher.py |
| P27.unitcost | 27 | A unit-cost model and a pilot-first go/no-go before the full 34-agent build | DEFERRED | DEFERRED (costed pilot - roadmap Phase 4) | — |
| P28.dag | 28 | A resumable idempotent cycle DAG that degrades per Part 19 | PARTIAL | gpu_agent/cycle.py (cycle plan plus log; sequential single-command); resume and DAG deferred | tests/test_cli_cycle_plan.py |
| P28.schedule | 28 | Unattended scheduling and cross-agent rate-limit governance | DEFERRED | DEFERRED (scheduling - charter Part 38 Not yet) | — |
| P29.canaries | 29 | Extraction canaries plus freshness and shape monitors on inputs | DEFERRED | DEFERRED (source-health monitors not built) | — |
| P29.degrade | 29 | Source-down triggers last-known-good plus a flag, never a silent substitution | PARTIAL | gpu_agent/gathering/dedup.py (drops logged) plus gpu_agent/cycle.py | tests/test_dedup_seen_docs.py |
| P30.queue | 30 | The human gate is a throughput-managed system with SLOs and auto-clear | DEFERRED | DEFERRED (review queue not built; no Main) | — |
| P31.secrets | 31 | Secrets in a vault, encryption at rest, an audit log of every human read | NOT-ENFORCED | NOT ENFORCED - aspiration (env-var keys; no vault, encryption, or audit log in v1) | — |
| P32.fastbreak | 32 | A mechanistic, material but not-yet-persistent signal may escalate as a capped hypothesis | DEFERRED | DEFERRED (fast-break path not built; needs Layer and Main) | — |
| P32.escalation | 32 | Escalation over silent override: an overruled sub-signal leaves a visible trace | DEFERRED | DEFERRED (tier override trace not built; needs Layer and Main) | — |
| P33.migration | 33 | Schema evolves across versions via a read-compat layer and a deprecation policy | PARTIAL | docs/migrations/2026-07-contract-v1.4.md (register kept); read-compat layer and deprecation policy deferred | — |
| P33.frozen | 33 | The contract is frozen within a version; frozen-core changes ship as migrations | ENFORCED | gpu_agent/schema/finding.py (schemaVersion) plus the eval hash-pin | tests/test_evals_baseline_pin.py |
| P34.coldstart | 34 | Seed a credible past via replay so the system is an analyst on day one | DEFERRED | DEFERRED (backtest and seeded backfill - not built) | — |
| P35.surface | 35 | The product surface specified to the same bar (SSO, push and pull, API contract) | DEFERRED | DEFERRED (product surface - roadmap Phase 7) | — |
| P36.harnesssearch | 36 | Search the harness as code, gated the same way as hand-written code | DEFERRED | DEFERRED (harness optimization - not built; gated on a trustworthy reward) | — |
| P37.gatherer | 37 | Gatherer swarm follows the trail with brakes; every truncating cap is logged | PARTIAL | gpu_agent/gathering/ingest.py plus SESSION-PROSE (four caps and on-topic filter, .claude/skills/gather-category/SKILL.md) | tests/test_gather_integration.py |
| P37.ingestseam | 37 | The ingest seam turns raw blobs into validated, de-duplicated, tier-stamped RawDocuments | ENFORCED | gpu_agent/gathering/ingest.py plus gpu_agent/schema/raw_document.py | tests/test_ingest.py |
| P37.webreach | 37 | Web-reach tools are a data registry; their output is secondary; ensure-installed idempotently | ENFORCED | registry/web-reach-tools.json plus gpu_agent/web_reach_ensure.py | tests/test_web_reach_registry.py |
| P37.caps | 37 | Gatherers return raw material only; a discovery tool's synthesized brief is never ingested | SESSION-PROSE | SESSION-PROSE (roles doctrine; .claude/skills/gather-category/SKILL.md) | — |
| P37.trusttier | 37 | Trust tier stamped deterministically at ingest; a secondary-only finding is confidence-capped | ENFORCED | gpu_agent/gathering/ingest.py (tier stamp) plus gpu_agent/gate.py (F2e) plus gpu_agent/publisher.py | tests/test_gate_corroboration.py |
| P38.uniform | 38 | Uniform tier interface run(scope, store); deferred tiers drop in with zero orchestrator change | PARTIAL | gpu_agent/cycle.py (driver over tier-stages); Layer and Main stages are stubs | tests/test_cycle_plan.py |
| P38.cyclelog | 38 | A cycle writes a replayable cycle log; a coverage gap is visible, never implied | ENFORCED | gpu_agent/cycle.py plus gpu_agent/store.py | tests/test_store_cycle_log_integrity.py |
| P38.tiers | 38 | The Layer and Main tiers, canonical store, parallelism, scheduling | DEFERRED | DEFERRED (charter Part 38 Not yet - roadmap Phases 3 to 7) | — |
| P38.assignlog | 38 | A selected category with no assignment is logged as skipped, never silently dropped | ENFORCED | gpu_agent/assignment.py plus gpu_agent/cycle.py | tests/test_assignment_category.py |
| P39.wiki | 39 | LLM-wiki threads: code-owned header, brain-curated body, cited finding history | ENFORCED | gpu_agent/wiki/store.py plus gpu_agent/wiki/page.py plus gpu_agent/wiki/log.py | tests/test_wiki_store.py |
| P39.indices | 39 | Momentum (trailing) and Outlook (forward) indices computed in code, additive fields | ENFORCED | gpu_agent/registry/horizon.py plus gpu_agent/registry/tracks.py plus gpu_agent/scoring.py | tests/test_registry_horizon.py |
| P39.discovery | 39 | Discovery lane plus bounded rabbit-holing for topics we did not define | PARTIAL | gpu_agent/wiki/lifecycle.py (provisional threads) plus SESSION-PROSE (follow-the-trail brakes) | tests/test_lifecycle_promotion.py |
| P39.momentum | 39 | Salience and materiality computed in code, never brain-invented; every drop logged | ENFORCED | gpu_agent/wiki/salience.py plus gpu_agent/wiki/lint.py | tests/test_wiki_lint_materiality.py |

## Findings

The matrix is honest by construction; these are the rows that are thinner than the charter's language
implies. **No new backlog items are minted here** — this is surfaced for the user to triage at merge
review (some already have open backlog items, noted inline).

### Genuine gaps — reads as binding, enforced by nothing (`NOT-ENFORCED`)

1. **P21.resolve — entity alias canonicalization and per-category namespacing (Part 21, Part 18 registry).**
   The charter's Part 18 fixed-contract registry lists `aliases` / `appearsIn` / `primaryCategory`, and
   Part 21 says a multi-category entity "must be counted once." Reality: there is no entity-registry file
   and no alias-resolution code — `NVDA` and `nvidia` are not reconciled, and the entity id is global.
   Already tracked as **F24** (open, Should-have). This is the closest analogue to the F2/F3/F5 pattern:
   a Part-18 "fixed contract" element that is, today, aspiration.
2. **P23.access — role-based human access + data classification (Part 31/23).** No access control or
   classification exists in v1. Part 31 frames the store as confidential CI; the control is absent.
3. **P31.secrets — vault, encryption at rest, audit log (Part 31).** API keys live in environment
   variables; there is no vault, no encryption at rest, and no human-read audit log. Expected for a local
   research build, but the charter states it as a rule, so it is recorded as unenforced, not silently assumed.

### `PARTIAL` rows worth watching (staged or scoped enforcement)

- **P20.stamp (Part 20).** Provenance is stamped at the **scorecard** level (`assignment@version` only),
  not the full per-Finding stamp (`modelId`, `promptVersion`, `taxonomyVersion`, `registryVersion`,
  `runId`) the charter specifies. Reproducibility currently leans on the recorded-replay path (P20.replay),
  not on a complete stamp.
- **P26.corroboration / P26.circular (Part 26).** Hard corroboration is deliberately **staged** (the
  three-distinct-publisher step, F63/F72) — the full Part 26 hard-corroboration requirement and a
  near-duplicate shingle pass are deferred by decision (contract v1.4). This is acknowledged in the charter,
  so it is `PARTIAL`, not a silent gap — but it is the single most security-relevant staged item.
- **P8.injection / P26.privsep / P37.caps / P22.allowlist.** The adversarial boundary is real but leans on
  **skill prose** for the tool-less-dispatch, raw-material-only, and paywall pieces; only the extraction-
  prompt delimiting (F16) is code-enforced. If the gather skills are ever bypassed, these clauses have no
  code backstop.

### Enforced-but-unpinned (code enforces it, no dedicated test names it)

- **P16.version (Part 16)** — the taxonomy version-bump-on-structural-change is not pinned by a test.
- **P33.migration (Part 33)** — the migration register is a doc convention; the read-compat layer and
  deprecation policy it promises are not built, so there is nothing to pin yet.

### The good news

The in-force **explainability doctrine** — Part 1 (rules 1-7), Part 2 (field rules), the entire Part 7
gate checklist, Part 8 guardrails, and Part 17's rating and anchor rules — is genuinely code-enforced and
test-pinned. That is exactly the surface where F2, F3, and F5 had drifted into aspiration; the matrix
confirms the drift is closed and gives a lint that will catch it if it reopens.
