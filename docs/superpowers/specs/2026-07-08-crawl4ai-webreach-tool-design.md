# Design — crawl4ai as web-reach `fetch` tool #3

**Date:** 2026-07-08
**Status:** approved (design), pending spec review
**Branch/worktree:** `feat/crawl4ai-webreach` / `.worktrees/crawl4ai`

## Goal

Give every category agent's gather cycle access to
[unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) — an LLM-friendly web crawler
that renders pages in a managed headless browser (Chromium via Playwright) and returns clean
Markdown. It joins the web-reach layer as **tool #3**, complementary to the built-in
WebSearch/web_fetch and to the two existing registered tools.

## Why this is a data entry, not a doctrine change

The web-reach layer (F69) is a *data-driven* registry (`registry/web-reach-tools.json`)
explicitly built so "a 2nd github drops in as a data entry"; F70 proved the pattern by adding
`last30days`. Per `docs/web-reach.md` ("Adding a tool"): adding a **same-role** tool "needs no
skill or charter edit — every category agent picks it up on the next run." crawl4ai is a
**`fetch`-role** tool — it returns raw page content ingested as `secondary` blobs, exactly like
`agent-reach`. Because the role already exists, no new doctrine is introduced.

### Niche vs. agent-reach (the existing fetch tool)

`agent-reach`'s web path uses Jina Reader (static extraction). crawl4ai runs a **real headless
browser**, so it is the fetch tool for **JavaScript-rendered / dynamic pages** that a static
reader cannot render. The two fetch tools are complementary, not redundant; both are consulted
each cycle and both feed the same `secondary` blob path.

## crawl4ai facts (verified 2026-07-08)

- **Install:** `pip install -U crawl4ai`, then `crawl4ai-setup` (downloads a Chromium browser
  via Playwright — a heavy first-time install, idempotent thereafter).
- **CLI:** `crwl <url> -o markdown` (output formats: `markdown`, `json`, `markdown-fit`, `all`;
  `-q <question>` for LLM Q&A; `-v` verbose).
- **Health probe:** `crwl --help` — fast, exits 0 when the console script is installed, and does
  **not** launch a browser. (`crawl4ai-doctor` exists but launches a browser and runs a test
  crawl, so it is too heavy for a per-run health check.)
- **What it is:** "Crawl4AI turns the web into clean, LLM-ready Markdown for RAG, agents, and
  data pipelines," using a managed browser for full JS rendering and dynamic-content extraction.

## Registry entry (the change)

Append one object to `tools[]` in `registry/web-reach-tools.json`:

```json
{
  "id": "crawl4ai",
  "enabled": true,
  "role": "fetch",
  "repo": "https://github.com/unclecode/crawl4ai",
  "installDocUrl": "https://docs.crawl4ai.com/core/installation/",
  "healthCmd": {
    "windows": "crwl --help",
    "macos": "crwl --help",
    "linux": "crwl --help"
  },
  "install": {
    "windows": [
      "py -3 -m pip install --user pipx",
      "py -3 -m pipx install crawl4ai",
      "py -3 -m pipx ensurepath",
      "crawl4ai-setup"
    ],
    "macos": [
      "python3 -m pip install --user pipx || brew install pipx",
      "pipx ensurepath",
      "pipx install crawl4ai",
      "crawl4ai-setup"
    ],
    "linux": [
      "python3 -m pip install --user pipx",
      "python3 -m pipx ensurepath",
      "pipx install crawl4ai",
      "crawl4ai-setup"
    ]
  },
  "invokeHint": "crwl <url> -o markdown   # headless-browser crawl -> clean markdown; -o json|markdown-fit|all, -q <question>",
  "capabilities": ["web", "crawl", "markdown", "javascript-render", "deep-crawl", "structured-extract"],
  "defaultTier": "secondary",
  "notes": "FETCH role - LLM-friendly crawler that renders pages in a managed headless browser (Chromium via Playwright), so it reaches JavaScript / dynamic pages agent-reach's Jina-Reader path cannot. Returns clean markdown ingested as secondary blobs: confidence-capped, gated, and chased toward a primary like any open-web page. The paywalled boundary still holds - never point crwl at licensed/inventoried sources (SemiAnalysis, TrendForce, ...). Install via pipx (isolated) + crawl4ai-setup (downloads Chromium); healthCmd is a fast console-script presence check that does not launch a browser."
}
```

### Design decisions baked into the entry

- **`enabled: true` (user-approved 2026-07-08).** `web-reach-ensure` auto-installs it on the
  operator's machine, including the Chromium download, so the gatherer can use it immediately
  every cycle. Heavy first install; idempotent afterward.
- **pipx isolation**, consistent with `agent-reach`. crawl4ai's dependency tree is heavy and must
  not pollute the repo `.venv`; pipx exposes the package's console scripts (`crwl`,
  `crawl4ai-setup`) on PATH. Installed artifacts are never committed.
- **`healthCmd` = `crwl --help`** on every OS — fast, browser-free, and free of the bare-`python3`
  Store-alias trap that `tests/test_web_reach_registry.py::test_windows_healthcmd_avoids_store_alias_python3`
  forbids on Windows.

## Docs

`docs/web-reach.md` — add crawl4ai to the "What it is" registered-tools bullet list (fetch role;
headless-browser / JS-rendering niche). The "Adding a tool" section already documents that a
same-role tool needs no skill/charter edit, so no other prose changes.

## Tests

`tests/test_web_reach_registry.py` — add `test_crawl4ai_registered_as_fetch`, mirroring
`test_last30days_registered_as_discovery`: assert the entry exists, `enabled is True`, and
`role == "fetch"`. The existing generic tests already cover the new object automatically:

- required fields present (`healthCmd`, `installDocUrl`, non-empty `capabilities`),
- valid `role` in `{fetch, discovery}`,
- unique ids,
- per-OS `install` recipes (non-empty string lists) and per-OS `healthCmd`,
- Windows `healthCmd` avoids bare `python3`.

## Deliberately NOT touched

- **`.claude/skills/gather-category/SKILL.md`** — its fetch-tool contract is already role-aware
  and reads the registry generically; crawl4ai rides the existing fetch path with no skill edit.
- **`docs/agent-swarm-charter.md` (Part 37)** — no new role, so no doctrine change. (Bonus:
  leaving the charter untouched also avoids colliding with the live `dashboard-showcase` lane's
  uncommitted charter edit on the root checkout.)

## Out of scope / non-goals

- No change to scoring, corroboration math, the frozen contract core, or emitted brain prompts —
  therefore the F6 baseline pin (`tests/test_evals_baseline_pin.py`) stays green.
- No per-machine secrets are required (crawl4ai's core crawl works without API keys); optional
  LLM-extraction keys are the operator's own setup, out of scope here.
- Not verified on macOS/Linux hardware — the non-Windows recipes are authored from crawl4ai's
  install docs and unit-tested for shape only, matching the standing platform note in
  `docs/web-reach.md`.

## Verification

- `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py` green (new + generic tests).
- Full suite green (expect 5 skips), F6 pin unaffected.
- Live smoke (operator machine, optional): `scripts/web-reach-ensure` installs crawl4ai and
  `crwl --help` exits 0; a real `crwl <url> -o markdown` returns markdown.

## Process

TDD in the `.worktrees/crawl4ai` lane (test first), suite green throughout, stop before merge,
write `.superpowers/handoffs/crawl4ai-webreach-DONE.md`. **Only the user merges to main.**
