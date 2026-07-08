# crawl4ai Web-Reach Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) as web-reach `fetch` tool #3 so every category agent's gather cycle can use its headless-browser crawler for JS/dynamic pages.

**Architecture:** Pure data + docs + test change. The web-reach layer (F69/F70) is a data-driven registry (`registry/web-reach-tools.json`); a same-role (`fetch`) tool is added as one JSON object, picked up generically by `gather-category` and `web-reach-ensure` with no skill or charter edit.

**Tech Stack:** Python 3 / pytest; JSON registry; pipx install; crawl4ai CLI (`crwl`).

## Global Constraints

- Work in the claimed worktree `.worktrees/crawl4ai` on branch `feat/crawl4ai-webreach`. Never edit root `main`. Run Python from the shared root venv: `../../.venv/Scripts/python` (repo-root paths in commands below assume you are `cd`'d into the worktree root).
- `git log --oneline -1` immediately before every commit; if HEAD is not your last commit, reconcile before committing.
- Suite must be green at the end (baseline: **1117 passed, 5 skipped**). No change may touch emitted brain prompts — the F6 pin `tests/test_evals_baseline_pin.py` must stay green (this change touches none).
- Stage files explicitly (never `git add -A`) — the root checkout has another lane's uncommitted files; do not sweep them.
- **Do NOT touch** `.claude/skills/gather-category/SKILL.md` or `docs/agent-swarm-charter.md` — same-role tool needs no doctrine change, and the charter is mid-edit in another lane.
- Commit trailer names the actual model: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- The registry entry must be exactly the object specified in the spec (`docs/superpowers/specs/2026-07-08-crawl4ai-webreach-tool-design.md`).

---

### Task 1: Add crawl4ai as web-reach `fetch` tool (registry + test + doc)

**Files:**
- Modify: `tests/test_web_reach_registry.py` (add one test after the `test_last30days_registered_as_discovery` block, ~line 84)
- Modify: `registry/web-reach-tools.json` (append one object to `tools[]`)
- Modify: `docs/web-reach.md` (add one bullet to the "What it is" registered-tools list, ~lines 10-16)

**Interfaces:**
- Consumes: `_load()` helper already in `tests/test_web_reach_registry.py` (reads and parses the registry).
- Produces: a `tools[]` entry with `id == "crawl4ai"`, `enabled == True`, `role == "fetch"`, plus per-OS `install`/`healthCmd`, `capabilities`, `defaultTier`, `notes`. The existing generic tests (`test_enabled_tools_have_required_fields`, `test_every_enabled_tool_has_valid_role`, `test_tool_ids_are_unique`, `test_enabled_tools_have_per_os_install_recipes`, `test_enabled_tools_have_per_os_healthcmd`, `test_windows_healthcmd_avoids_store_alias_python3`) automatically apply to it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_web_reach_registry.py`, immediately after `test_last30days_registered_as_discovery` (mirror its shape):

```python
# --- crawl4ai (fetch-role) tool #3 ---


def test_crawl4ai_registered_as_fetch():
    t = next((x for x in _load()["tools"] if x["id"] == "crawl4ai"), None)
    assert t is not None
    assert t["enabled"] is True
    assert t["role"] == "fetch"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_web_reach_registry.py::test_crawl4ai_registered_as_fetch -v`
Expected: FAIL — `assert t is not None` fails (`t` is `None`; no such tool yet).

- [ ] **Step 3: Add the registry entry**

In `registry/web-reach-tools.json`, append this object to the `tools[]` array (after the `last30days` object — add a comma after the closing `}` of the `last30days` entry). Use exactly this content:

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

- [ ] **Step 4: Run the test to verify it passes + the whole registry test file**

Run: `../../.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -v`
Expected: PASS — the new test passes AND every generic test (required-fields, valid-role, unique-ids, per-OS install/healthCmd, no-bare-python3) still passes over the new object. If the JSON fails to parse, `test_registry_parses_and_has_version` fails first — check the comma you added after the `last30days` object.

- [ ] **Step 5: Update the operator doc**

In `docs/web-reach.md`, the "What it is" section lists registered tools. After the `last30days` bullet (the block ending "...ranked by social engagement."), add this bullet at the same indentation:

```markdown
  - `crawl4ai` (https://github.com/unclecode/crawl4ai) — **fetch** role: an LLM-friendly
    crawler that renders pages in a managed headless browser (Chromium via Playwright), so it
    reaches JavaScript / dynamic pages agent-reach's static Jina-Reader path cannot. Returns
    clean markdown ingested as `secondary` blobs.
```

- [ ] **Step 6: Confirm the doc test and full registry test file still pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -q`
Expected: all pass (includes `test_web_reach_doc_exists_and_points_at_registry`).

- [ ] **Step 7: Commit**

```bash
git log --oneline -1   # verify HEAD is your last commit (the spec commit b002f74)
git add tests/test_web_reach_registry.py registry/web-reach-tools.json docs/web-reach.md
git commit -F - <<'EOF'
feat: add crawl4ai as web-reach fetch tool #3

Registers unclecode/crawl4ai in registry/web-reach-tools.json as a fetch-role
tool (enabled): a headless-browser crawler (Chromium via Playwright) that
returns clean markdown for JS/dynamic pages agent-reach's Jina path can't
render. Same-role data entry per the F69 web-reach layer + F70 precedent -
no skill or charter edit. pipx-isolated install + crawl4ai-setup; healthCmd
'crwl --help' (fast, browser-free, avoids the Windows python3 Store-alias trap).
Adds test_crawl4ai_registered_as_fetch; generic registry tests cover the rest.
Doc bullet added to docs/web-reach.md.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 2: Lane-finish — full-suite verification + DONE sentinel

**Files:**
- Create: `.superpowers/handoffs/crawl4ai-webreach-DONE.md`

**Interfaces:**
- Consumes: the committed feature from Task 1.
- Produces: a completion sentinel that signals the lane is ready for the user to merge.

- [ ] **Step 1: Run the full suite**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: **1118 passed, 5 skipped** (baseline 1117 + the one new test). Confirm `tests/test_evals_baseline_pin.py` is NOT red (this change touches no emitted prompt).

- [ ] **Step 2: (Optional, operator-gated) live smoke of the install + health path**

Only if the user wants to install crawl4ai now (heavy first-time Chromium download, a few minutes). This mutates the machine (installs software) — confirm before running:

Run: `scripts/web-reach-ensure` (from repo root) — expect it to install crawl4ai idempotently, then `crwl --help` to exit 0. A deeper check: `crwl https://example.com -o markdown` returns markdown.
If skipped, note that the install will happen automatically on the next live cycle's web-reach preamble (the entry is `enabled`).

- [ ] **Step 3: Write the completion sentinel**

Create `.superpowers/handoffs/crawl4ai-webreach-DONE.md`:

```markdown
# DONE — crawl4ai web-reach fetch tool #3 (lane: feat/crawl4ai-webreach)

- **Date:** 2026-07-08
- **Branch/worktree:** `feat/crawl4ai-webreach` / `.worktrees/crawl4ai`
- **Merge state:** NOT merged — awaiting user merge to main (only the user merges).
- **Commits:** `b002f74` (spec) + <Task-1 feat hash>.
- **What shipped:** crawl4ai registered in `registry/web-reach-tools.json` as fetch tool #3
  (enabled, role=fetch, pipx install + crawl4ai-setup, healthCmd `crwl --help`);
  `test_crawl4ai_registered_as_fetch` added; `docs/web-reach.md` bullet added.
- **Not touched:** `gather-category/SKILL.md`, charter Part 37 (same-role tool, no doctrine change).
- **Suite:** 1118 passed / 5 skipped; F6 pin green.
- **Live install:** <ran web-reach-ensure smoke | deferred to next live cycle>.
- **Next session must know:** to merge, `git merge --no-ff feat/crawl4ai-webreach` from main,
  re-run the suite, then delete branch + `git worktree remove .worktrees/crawl4ai`, and update
  `docs/superpowers/HANDOFF.md`.
```

- [ ] **Step 4: Commit the sentinel + STOP**

```bash
git log --oneline -1
git add .superpowers/handoffs/crawl4ai-webreach-DONE.md
git commit -F - <<'EOF'
docs(handoff): crawl4ai-webreach DONE sentinel — awaiting user merge

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

Do NOT merge. Report the branch, commits, and suite status to the user and wait for the merge go.

---

## Self-Review

- **Spec coverage:** registry entry (Task 1 Step 3 — verbatim from spec), `test_crawl4ai_registered_as_fetch` (Task 1 Step 1), generic tests noted as auto-covering (Task 1 Step 4), doc update (Task 1 Step 5), NOT-touched files (Global Constraints + Task 1), F6-pin-unaffected + full-suite verification (Task 2 Step 1), optional live smoke (Task 2 Step 2), DONE sentinel + stop-before-merge (Task 2 Steps 3-4). All spec sections map to a task.
- **Placeholder scan:** the only bracketed placeholders are `<Task-1 feat hash>` and the live-install status line inside the sentinel template — both are values filled in at execution time, not undefined work. No "TBD/TODO/handle edge cases".
- **Type consistency:** the test reads `id`/`enabled`/`role` — the exact keys present in the registry object. `_load()` is the existing helper. Field names (`healthCmd`, `install`, `capabilities`, `defaultTier`) match the generic tests' expectations.
