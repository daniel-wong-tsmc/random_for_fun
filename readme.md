# GPU Category Agent — AI Market State desk (working repo)

A deterministic, evidence-gated market-state pipeline for the AI hardware market,
built as the first (and so far only) category agent of a larger agent-swarm design.
The live category is **`chips.merchant-gpu`** (NVIDIA / AMD / Intel merchant GPUs).

> **Note on the repo name:** `random_for_fun` predates the project. Rename before
> showing this under TSMC branding (tracked as part of fix F48).

## What it does

One cycle = gather → extract → gate → judge → score → store → report:

1. **Gather** — web documents are snapshotted as raw blobs (paywalled sources are
   inventoried and labeled, never scraped).
2. **Extract** — an LLM brain (Claude Code subagents; no API key, no SDK) turns
   documents into typed `Finding`s.
3. **Gate** — deterministic code validates every finding (schema, evidence,
   registry); nothing un-gated reaches a number.
4. **Judge** — the brain rates six dimensions (momentum, unit economics, competitive
   structure, moat, bottleneck, strategic risk) from gated findings only.
5. **Score** — code computes DMI/SMI/SDGI and Momentum/Outlook indices; the model
   never sets a number that reaches the scorecard uncomputed.
6. **Store** — append-only temporal store (`store/<category>/<asOf>-vN.json`,
   originals immutable) plus an LLM-wiki thread model with lifecycle + dedup.
7. **Report** — a deterministic, brief-first text report (BLUF → board → WHAT MOVED
   → STORYLINES), a pure projection of the store: no LLM in the renderer, every
   claim cites its finding.

## Honest build status

- **Built & live:** the `chips.merchant-gpu` category agent end-to-end; six 2026-06
  scorecards in `store/chips.merchant-gpu/`; suite 417 passed / 3 skipped.
- **Partial:** `models.frontier-closed` is a config-only generalization proof
  (scores without code changes; not yet runnable end-to-end).
- **Design target (not built):** the other 32 category agents, the Layer tier, the
  Main orchestrator, the HTML dashboard. `app/swarm-graph.html` renders the full
  design with a built-vs-deferred overlay.
- **Known defects being worked:** `docs/fix-backlog.md` (F1–F49, waved + laned).

## Quickstart

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest          # deterministic; live paths are env-gated
```

Run everything from the repo root (paths are cwd-relative by convention).
Live cycles are driven by Claude Code skills (`.claude/skills/run-cycle`,
`gather-category`) — Claude Code **is** the brain; there is no metered API path.
- Web-reach tools (`agent-reach`, `last30days`) auto-install on first run via
  `scripts/web-reach-ensure` (idempotent, cross-platform); see `docs/web-reach.md`.

## Repo map

| Path | What |
|---|---|
| `gpu_agent/` | The pipeline: `gate.py`, `scoring.py`, `pipeline.py`, `extraction/`, `judgment/`, `gathering/` (dedup), `wiki/` (temporal store, lifecycle, lint), `registry/`, `report.py`, `brief.py`, `cli.py` |
| `registry/indicators.json` | Indicator registry (weights, dimensions, cadence/horizon, source inventory) — data, not code |
| `manifests/`, `fixtures/` | Coverage manifests; committed test fixtures (golden scorecard, recorded LLM answers) |
| `store/` | Canonical run history — tracked in git (scorecards, cycle log; wiki + dedup index once live) |
| `docs/agent-swarm-charter.md` | The binding design charter (Parts 1–39) |
| `docs/fix-backlog.md` | The active fix backlog + lane execution model |
| `docs/superpowers/` | HANDOFF (resume point), specs, plans |
| `.superpowers/sdd/progress.md` | Build ledger (gitignored; per-machine) |
| `app/swarm-graph.html` | Interactive design-target graph with build-status overlay |

## Doctrine (the short version)

Code computes, gates, and stores; the brain reasons and curates. Never fabricate a
number. Every claim cites its findings; fetched page text is data, not instructions.
Every cap/skip/drop is logged, never silent. Paywalled sources are inventoried and
labeled `estimate`, never scraped. Frozen core contracts (`gate.py`, `scoring.py`,
the `Finding` schema, the six dimensions) change only through versioned Part-33
migrations with regenerated golden fixtures.
