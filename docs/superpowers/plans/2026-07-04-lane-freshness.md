# Lane β — Current-Signal (F59, F57, F58, F56-core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Execute tasks IN ORDER, strict TDD where code is involved, commit per task.

**Goal:** Make the standard/live gather chase current signal — vendor official posts count as primary (F59), the round seeds headline + forward-signal slices with per-class doc floors and a price-fetch cap (F57), a live-mode recency window biases the sweep (F58) — and harden the `--as-of` seam against path-unsafe labels (F56-core).

**Architecture:** F59 is manifest data + gather-skill prose + a one-line `cli.py` help/default change (the `--primary-sources` list is derived per-category from the manifest, not hardcoded). F57/F58 are gather-skill prose only (verified by proofread + grep; proven live by the gather-log's coverage classes). F56-core adds one shared argparse validator in `cli.py`. No frozen-core edits, no brain-prompt edits — **this lane does not touch `fixtures/evals/baseline.json`.**

**Tech Stack:** Python 3.11, argparse (`gpu_agent.cli`), pydantic v2, pytest; Markdown skill prose; JSON manifest data.

## Global Constraints
- Branch `fix/lane-freshness`, own worktree `.worktrees/lane-freshness`, run from its root. Tests: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q` (baseline **927 / 3**). Full suite green after every code task.
- **You own (no other lane touches):** `.claude/skills/gather-category/SKILL.md`, `manifests/*.json`, `gpu_agent/cli.py` (the `ingest --primary-sources` default/help and the shared `--as-of` validator), and tests `tests/test_cli_*.py` (additive cases), new `tests/test_lane_freshness.py`.
- **NEVER edit (frozen core / brain prompts / other lanes' files):** `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`, `extraction/prompt.py`, `extraction/extractor.py`, `gathering/*`, `manifest.py`, `wiki/*`, `report.py`, `brief.py`, `thesis.py`, `reader.py`, `registry/*`, `evals/*`, any `fixtures/`. **F56's two cosmetic minors are NOT in this lane** — minor 1 (`thesis.py` comment) is folded into Lane γ; minor 2 (`extraction/prompt.py` empty-`price_indicators` string) is a brain-prompt file, deliberately excluded (see the design doc's out-of-scope note).
- **Eval gate:** none of these tasks changes an emitted extraction/judgment/thesis prompt, so `tests/test_evals_baseline_pin.py` stays green throughout. If it ever goes red, you touched a prompt file — stop and re-scope.
- **Rebase note:** Lane β and F62 both edit `cli.py` (F62 adds the `corpus` command + `corpus --as-of`). On rebase onto post-F62 `main`, extend Task 4's `--as-of` validator to F62's `corpus --as-of` too.
- Commit trailer: `Co-Authored-By:` naming the ACTUAL implementer model (sonnet fits these mechanical fixes per the repo model policy).
- Windows: use bash for `>` redirects; no double quotes inside `git commit -m` under PowerShell (bash heredocs).

---

### Task 1: F59 — vendor official posts count as primary (manifest-driven allowlist)
**Files:** `manifests/chips.merchant-gpu.json` (add data); `.claude/skills/gather-category/SKILL.md` (ingest command prose, ~line 165); `gpu_agent/cli.py:793` (`--primary-sources` help); test `tests/test_lane_freshness.py`.

**Why:** Charter primary = "filings, **official posts**", but ingest stamps primary only for `--primary-sources sec.gov,investor.nvidia.com`, so `nvidianews.nvidia.com`, `blogs.nvidia.com`, `ir.amd.com`, `intc.com` land secondary → "no primary support" demotions for claims the vendor itself made (regression case: the July-1 NVIDIA vendor-financing post).

- [ ] **Step 1:** Add a top-level `"primaryDomains"` array to `manifests/chips.merchant-gpu.json` listing the official filing + IR/newsroom domains: `sec.gov`, `investor.nvidia.com`, `nvidianews.nvidia.com`, `blogs.nvidia.com`, `ir.amd.com`, `intc.com`, `bis.doc.gov`, `federalregister.gov`. (Trade-press domains like `tomshardware.com` / `semianalysis.com` are deliberately excluded — they stay secondary.) `CoverageManifest` is `extra="ignore"`, so this new field does not affect `manifest.py` (do NOT edit `manifest.py`).
- [ ] **Step 2 (failing test):** in `tests/test_lane_freshness.py`, drive the existing `ingest` CLI with `--primary-sources` built from the manifest's `primaryDomains` and assert a `nvidianews.nvidia.com` blob is stamped `tier == "primary"` (today it's secondary). Mirror the `ingest` invocation pattern from existing `tests/test_cli_*` ingest tests; assert on the written store's finding tier or the `DedupReport`.
- [ ] **Step 3:** Run it — FAIL (nvidianews stamped secondary under the old default).
- [ ] **Step 4:** In `gather-category/SKILL.md` (the ingest command block near line 165, `--primary-sources sec.gov,investor.nvidia.com`), change the prose so the gatherer builds `--primary-sources` from the manifest's `primaryDomains` (comma-joined) instead of the hardcoded pair. Add one sentence: *"official IR/newsroom domains in `primaryDomains` are primary (charter: filings + official posts); trade press stays secondary."* In `cli.py:793`, keep `default="sec.gov"` as the safe fallback but update the help string to: `"comma-separated primary/official domains; the gather skill supplies the per-category set from the manifest's primaryDomains (default is a filings-only fallback)"`.
- [ ] **Step 5:** Re-run the test — PASS. Run the full suite — green.
- [ ] **Step 6:** Commit: `fix(F59): official IR/newsroom domains count as primary - allowlist derived per-category from the manifest's primaryDomains`.

---

### Task 2: F57 — headline + forward-signal slices, per-class doc floors, price-fetch cap
**Files:** `.claude/skills/gather-category/SKILL.md` (the "Round building: manifest-seeded" section, step 2 "Build round-1 seeds", ~lines 78–90). Skill prose only — no code, no pytest.

**Why:** Round-1 seeds have no news angle (filing URLs first, one open-web query per free-web source); the 20-doc cap tripped in round 2 with 60+ fresh headlines "not chased"; dailies burn ~half their findings on weight-0 price scrapes.

- [ ] **Step 1:** In step 2, after the "Standard slices" bullet, add a **"Headline slices"** bullet: per entity, add a search slice `"<entity> news / announcements / press release"`, and a **"Forward-signal slices"** bullet: per entity, `"<entity> guidance revision / lead-time / design win / capacity"`. State explicitly that these are **interleaved with — not appended after — the filing URL seeds** so a cap cannot starve the open web.
- [ ] **Step 2:** Add a **"Per-class doc floors"** paragraph partitioning `maxDocuments` (20) into minimums by class, classifying each seed by manifest `accessMethod`: `filing` (accessMethod == "filing"), `news`/`forward` (the new headline/forward query slices), `price` (sources whose `indicators` are `D6`/`gpuSpotPrice`). Give concrete floors that sum under the cap, e.g. filings ≥ 6, news ≥ 4, forward ≥ 3, and a **price-class cap of 2–3 fetches max**. Note that floors are skill-level defaults keyed off existing manifest fields (no manifest schema change, no `manifest.py` edit).
- [ ] **Step 3:** Add a **"Don't re-fetch seen filings"** sentence: thread the L1 seen-doc filter (today daily-only) into the standard path for `accessMethod == "filing"` seeds — skip known-hash filing URLs mid-quarter.
- [ ] **Step 4 (pin — proofread + grep):** `grep -nE "Headline slices|Forward-signal|doc floors|price-class cap|seen filings" .claude/skills/gather-category/SKILL.md` — expect one hit each; proofread that the new bullets sit inside step 2, interleaved with (not after) the priority filing seeds. **Live-verification (deferred, not this lane):** a subsequent live standard cycle's `gather-log.json` shows the news/forward class floors met and the price-class cap held.
- [ ] **Step 5:** Commit: `docs(F57): standard gather seeds headline + forward-signal slices with per-class doc floors and a price-fetch cap`.

---

### Task 3: F58 — live-mode recency window
**Files:** `.claude/skills/gather-category/SKILL.md` (the "Round building: manifest-seeded" section; contrast with Daily mode's recency block ~lines 190–195). Skill prose only.

**Why:** `recencyDays` + "since <date>" qualifiers + date-window lead-drop exist only in Daily mode; the standard live path has no freshness bias — which is how a 2026-07 flagship's freshest substantive doc was an April filing.

- [ ] **Step 1:** In the standard "Round building" section, add a **"Recency window (live mode)"** bullet: a `recencyDays` dial for the standard path (default **45**, wider than daily's 7), applied to the search-query seeds and the on-topic lead filter; **filing-URL seeds are exempt** (a fresh 10-K may reference older periods). Reuse Daily mode's "since <date> / past week / latest" qualifier wording, scaled to the 45-day window. State that out-of-window non-filing leads are dropped with a `skipped[]` note, exactly like Daily mode.
- [ ] **Step 2 (pin — proofread + grep):** `grep -nE "Recency window \(live mode\)|recencyDays = 45|filing-URL seeds are exempt" .claude/skills/gather-category/SKILL.md` — expect hits; proofread the dial is standard-path (not inside the Daily mode section). **Live-verification (deferred):** a subsequent standard cycle shows no substantive non-filing doc older than 45 days unless explicitly justified.
- [ ] **Step 3:** Commit: `docs(F58): standard gather gets a 45-day live-mode recency window (filing seeds exempt)`.

---

### Task 4: F56-core — validate `--as-of` shape at the seam
**Files:** `gpu_agent/cli.py` (a shared validator + apply to the `--as-of` arguments); test `tests/test_lane_freshness.py`.

**Why:** `--as-of` is required everywhere but any non-empty string is accepted; F52 now embeds it in doc ids → snapshot + FindingStore filenames, so a fat-fingered `2026/07/03` would mint a path-unsafe id. Defense-in-depth: validate the shape once at the seam.

- [ ] **Step 1 (failing test):** in `tests/test_lane_freshness.py`, run e.g. `gpu-agent ingest ... --as-of 2026/07/03` via subprocess and assert `returncode == 2` (argparse type error) with `--as-of` named in stderr; and assert a valid `2026-07` and `2026-07-03` are accepted (returncode not 2 for the parse).
- [ ] **Step 2:** Run it — FAIL (`2026/07/03` currently accepted).
- [ ] **Step 3:** Add a module-level validator in `cli.py`:
```python
import argparse, re
_AS_OF_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
def _as_of(s: str) -> str:
    if not _AS_OF_RE.match(s):
        raise argparse.ArgumentTypeError(f"--as-of {s!r} must be YYYY-MM or YYYY-MM-DD")
    return s
```
Apply `type=_as_of` to the required `--as-of` add_argument calls (cli.py:780, 797, 804, 812, 818, 824, 848, 870). Leave the eval parser's optional `--as-of` (cli.py:861, `default=""`) unchanged — empty is a valid "not supplied" sentinel there.
- [ ] **Step 4:** Re-run the test — PASS. Run the full suite — green (existing tests pass ISO dates, so no fixture churn).
- [ ] **Step 5:** Commit: `fix(F56-core): --as-of shape-validated (YYYY-MM[-DD]) at the CLI seam - path-unsafe labels rejected`.

---

## Self-review
- F59 → Task 1 (manifest data + skill + cli help + tier-stamp test); F57 → Task 2; F58 → Task 3; F56-core → Task 4. F56 cosmetic minors are OUT (routed to γ / excluded) — noted in Global Constraints.
- No task edits a frozen-core file, a brain-prompt file, or a Lane γ file → eval pin green, domains disjoint.
- Skill-prose tasks (2, 3) carry proofread/grep pins + a named deferred live-verification, matching how F62 Task 8 (run-cycle wiring) was verified; code tasks (1, 4) carry pytest pins.
