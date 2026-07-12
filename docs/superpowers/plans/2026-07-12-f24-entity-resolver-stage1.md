# F24 Stage 1 — Entity Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One canonical identity per entity for NEW data: known aliases (NVDA, Taiwan Semiconductor) normalize to canonical ids (nvidia, tsmc) at finding creation and at wiki page keying; unknown names pass through unchanged, flagged and counted per cycle.

**Architecture:** New `gpu_agent/entities.py` loads `docs/taxonomy.json` → `modularity.seedEntities` once (cached) and exposes `resolve(name) -> (canonical_id, registered)`. Seam A (`extraction/extractor.py` `extract_findings`) rewrites `Finding.entity` to the canonical id for REGISTERED names only, and collects unregistered names on `ExtractionOutcome`. Seam B (`wiki/ingest.py` `_entity_page_id`) resolves before slugging so no new alias-split pages are minted. Flag surface = stderr `UNREGISTERED-ENTITY` line (extract + pipeline CLI) plus a session-authored `unregisteredEntities` record in the cycle-log journal (run-cycle SKILL.md instruction — the journal has no code writer; it is session-authored at finalize).

**Tech Stack:** Python 3 + pydantic (repo standard), pytest. Venv: `../../.venv/Scripts/python` from worktree root. No new dependencies.

## Global Constraints (from the spec — violations are merge-blockers)

- **Zero emitted-prompt byte changes.** `tests/test_evals_baseline_pin.py` stays green. (Verified pre-plan: prompt hashes are emitted from FIXED raw seam inputs in `fixtures/evals/hash-input.json`; neither seam touches emitted bytes.)
- **Frozen core untouched:** `gate.py`, `scoring.py`, `schema/*` (NO new Finding fields), `judgment/briefing.py`, `judgment/judge.py` aggregation, `pipeline.py`, `sufficiency.py`, JsonStore (`store.py` / `wiki/store.py` write paths).
- **No `store/` data edits.** Stage 1 is code + tests + skill-doc only.
- **F25 merge-independence:** do NOT touch `gpu_agent/wiki/{log,store,lint,textscan,bench}.py`. `wiki/ingest.py` is free.
- Unregistered entities pass through flagged — never rejected, never a schema field.
- Suite green at EVERY commit (baseline 1200 passed / 5 skipped). `git log --oneline -1` before every commit. Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Commit messages via bash heredoc. LF canonical.
- Tests run from worktree root: `cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && ../../.venv/Scripts/python -m pytest -q`.

## Decision provenance

**User-approved (interactive, 2026-07-12 — spec + Q1/Q2/Q3 relay):**
1. Scope = stage 1, new data only; historical consolidation deferred (spec).
2. Unknown entities pass through flagged, never rejected (spec).
3. Data home = `docs/taxonomy.json` `seedEntities`, consumed in place via `gpu_agent/config.py` (spec).
4. Q1: migrate the existing test files so Seam B goes live for real; swap `entity:nvda`→`entity:nvidia` and routed titles ONLY where a finding is actually routed through `_entity_page_id`; leave manually-built `entity:nvda` pages alone; special care with `test_brief_movement.py` human-readable assertions.
5. Q2: unregistered names pass through UNCHANGED (flag + count only); `Finding.entity` is overwritten only when `registered=True`; `resolve()` still returns the slug form for unregistered.
6. Q3: flag surface = BOTH the stderr `UNREGISTERED-ENTITY` line (DROPPED pattern) AND a durable count+names record in the cycle log's run entry. The journal is session-authored (run-cycle SKILL.md Step 6), so the durable half is a SKILL.md instruction — no frozen code, no F74 journal-writer code exists to touch. (Fresh QUESTION-STOP only if that wiring turned out to need frozen code — it does not.)

**Trivial mechanical choices (this plan; do not re-litigate, do not escalate):**
- Alias map is keyed on the SLUGIFIED form of id/name/aliases (case-insensitivity plus whitespace/punctuation robustness in one rule; same regex as `wiki.ingest.slug`).
- Two seeds claiming the same alias key fail loud at load (`ValueError`).
- A taxonomy without `modularity.seedEntities` yields an EMPTY resolver (everything unregistered → exactly today's behavior); no crash.
- An unsluggable entity name (e.g. `"!!!"`) in Seam A is treated as unregistered (flagged with the raw name, finding not dropped); `resolve()` itself raises `ValueError` on empty-slug input, mirroring `wiki.ingest.slug` (Seam B behavior on such names is unchanged from today: loud failure at routing).
- Flag line format: `UNREGISTERED-ENTITY <n>: <name1>, <name2>` — n = count of DISTINCT names, names sorted, aggregated across the command's docs.
- Accessors return `None` / `()` for unregistered names instead of raising (unregistered is a legal state).
- `display_name(name)` accessor added for Seam B page titles: registered → seed's `name` (e.g. "NVIDIA"); unregistered → input unchanged.
- `ExtractionOutcome` (non-frozen pydantic model in `extraction/extractor.py`) gains `unregisteredEntities: list[str]` — additive, not a Finding schema change.
- `gathering/dedup.py` `prior_vintage` is left UNTOUCHED: in the live flow findings reach dedup after Seam A (entity already canonical), so its `entity:{slug(entity)}` lookup stays consistent; historical alias-keyed pages are stage 2. Also honors "leave manually-built pages alone" (dedup tests seed pages manually).
- Eval harness untouched: it grades raw answer text and gates via ok/violations only — entity values never feed grades or prompt hashes (verified in `gpu_agent/evals/harness.py`, `prompt_hash.py`, `cases.py`).

## Pinned seams (verified against source)

- **Seam A:** `gpu_agent/extraction/extractor.py::extract_findings` — the draft loop after `client.complete_json` validation, BEFORE `draft_to_finding`/gate. `draft_to_finding` itself stays dumb (tests call it directly with "NVDA" and must stay green). Not frozen core.
- **Seam B:** `gpu_agent/wiki/ingest.py::_entity_page_id` (used by both `route_findings` and `build_bundle`) + the `store.create_page(pid, "entity", f.entity, ...)` title in `route_findings`.
- **Flag surfaces:** `gpu_agent/cli.py::_extract` (after the doc loop, next to the DROPPED prints) and `gpu_agent/cli.py::_pipeline` (same); `.claude/skills/run-cycle/SKILL.md` Step 3(b) + Step 6.

## Seam B test-migration blast radius (surveyed; migrate in Task 4)

Routed-`NVDA` assertions (page id `entity:nvda` → `entity:nvidia`; routed page title `NVDA` → `NVIDIA`):
1. `tests/test_wiki_ingest_phase1.py` (touched list, observations, category, bundle pageId; `test_slug_normalizes` is about `slug()` itself — UNCHANGED)
2. `tests/test_wiki_ingest_apply.py` (enrichment pageId, window body path)
3. `tests/test_wiki_ingest_cli.py` (page file `nvda.md` → `nvidia.md`, bundle pageIds, recorded enrichment pageId)
4. `tests/test_wiki_v12.py` (salience/gate tests routing "NVDA" then reading `entity:nvda`)
5. `tests/test_brief_movement.py` (SPECIAL CARE: `"NVDA" in reg_titles` → `"NVIDIA"`; `s.title == "NVDA"` → `"NVIDIA"`; header/record_state calls on `entity:nvda` → `entity:nvidia`; AMD rows unchanged — AMD is unregistered)
6. `tests/test_brief_report.py` (one routed finding + header/state on `entity:nvda`)
7. `tests/test_w2_lane_f.py` (routed then `_score_move` on `entity:nvda`)
8. `tests/test_w2_lane_g.py` (`test_route_findings_crash_recoverable_...` observations + touched list; the page-path and config tests are untouched)
9. `tests/test_wiki_lint_materiality.py` (routed then `_score_move`/`record_state` on `entity:nvda`)
10. `tests/test_wiki_lint_cli.py` (routed + enrichment pageId `entity:nvda`)

NOT migrated (manually-built pages / no routing of registered aliases): `test_dedup_vintage.py`, `test_dedup_classify.py`, `test_dedup_cli.py` (routes only "AMD" — unregistered), `test_corpus_*`, `test_lifecycle_*`, `test_memory_bundle.py`, `test_wiki_lint_health.py`, `test_wiki_diff.py` (manual create_page), `test_golden_integration.py` (`run` loads pre-built findings; no extraction, no routing), `test_extraction_drafts.py` (calls `draft_to_finding` directly — below the seam).

## Acceptance-test map (spec's 6)

1. Alias resolution → `tests/test_entities.py` (Task 1)
2. Seam A canonical storage → `tests/test_extractor_entities.py` (Task 2)
3. Seam B canonical page slug → new tests in `tests/test_wiki_ingest_phase1.py` + migrated suite (Task 4)
4. Unregistered pass-through + per-cycle count → Tasks 2 (outcome field) + 3 (stderr line) + 5 (journal record)
5. `primaryCategory`/`appearsIn` accessors → `tests/test_entities.py` (Task 1)
6. F6 pin green; full suite green → every task's final step + Task 6 verification

---

### Task 0: Commit the plan

- [ ] **Step 1:** `git log --oneline -1` (HEAD must be 31dc909 or your own last commit).
- [ ] **Step 2:** Commit this plan file via bash heredoc:

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && git add docs/superpowers/plans/2026-07-12-f24-entity-resolver-stage1.md && git commit -F - <<'EOF'
docs(plan): F24 stage-1 entity-resolver implementation plan

Decision provenance: spec 2026-07-12 + user-answered Q1/Q2/Q3 (interactive relay).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

- [ ] **Step 3:** `git push -u origin f24-entity-resolver`.

---

### Task 1: `gpu_agent/entities.py` — the resolver

**Files:**
- Create: `gpu_agent/entities.py`
- Test: `tests/test_entities.py`

**Interfaces:**
- Produces: `EntityResolver` with `resolve(name: str) -> tuple[str, bool]`, `display_name(name: str) -> str`, `primary_category(name: str) -> str | None`, `appears_in(name: str) -> tuple[str, ...]`; module function `default_resolver() -> EntityResolver` (lru_cache(1), reads `config.TAXONOMY_PATH`). Consumed by Tasks 2 and 4.

- [ ] **Step 1: Write the failing tests** — `tests/test_entities.py`:

```python
import json
import pytest
from gpu_agent.entities import EntityResolver, SeedEntity, default_resolver

def _resolver():
    return EntityResolver([
        SeedEntity(id="nvidia", name="NVIDIA", aliases=["NVDA"],
                   primaryCategory="chips.merchant-gpu",
                   appearsIn=["chips.merchant-gpu", "chips.networking-silicon"]),
        SeedEntity(id="tsmc", name="TSMC", aliases=["Taiwan Semiconductor"],
                   primaryCategory="chips.foundry-packaging",
                   appearsIn=["chips.foundry-packaging"]),
    ])

# --- acceptance 1: alias resolution, case-insensitive, ticker + name variants ---

def test_ticker_name_and_id_variants_land_on_one_canonical_id():
    r = _resolver()
    for variant in ("NVDA", "nvda", "Nvidia", "NVIDIA", "nvidia"):
        assert r.resolve(variant) == ("nvidia", True), variant

def test_multiword_alias_resolves_case_insensitively():
    r = _resolver()
    assert r.resolve("Taiwan Semiconductor") == ("tsmc", True)
    assert r.resolve("taiwan semiconductor") == ("tsmc", True)
    assert r.resolve("  Taiwan   Semiconductor  ") == ("tsmc", True)  # whitespace-folded
    assert r.resolve("TSMC") == ("tsmc", True)

def test_unregistered_returns_slug_and_false():
    r = _resolver()
    assert r.resolve("AMD") == ("amd", False)
    assert r.resolve("Super Micro") == ("super-micro", False)

def test_resolve_is_deterministic():
    r = _resolver()
    assert r.resolve("NVDA") == r.resolve("NVDA") == ("nvidia", True)

def test_empty_slug_input_fails_loud():
    with pytest.raises(ValueError):
        _resolver().resolve("!!!")

def test_alias_collision_fails_loud_at_load():
    with pytest.raises(ValueError):
        EntityResolver([
            SeedEntity(id="nvidia", name="NVIDIA", aliases=["NVDA"],
                       primaryCategory="c", appearsIn=["c"]),
            SeedEntity(id="nvda-corp", name="NVDA", aliases=[],
                       primaryCategory="c", appearsIn=["c"]),
        ])

# --- acceptance 5: accessors return taxonomy truth ---

def test_primary_category_accessor():
    r = _resolver()
    assert r.primary_category("NVDA") == "chips.merchant-gpu"
    assert r.primary_category("nvidia") == "chips.merchant-gpu"
    assert r.primary_category("AMD") is None            # unregistered

def test_appears_in_accessor():
    r = _resolver()
    assert r.appears_in("Nvidia") == ("chips.merchant-gpu", "chips.networking-silicon")
    assert r.appears_in("AMD") == ()

def test_display_name_accessor():
    r = _resolver()
    assert r.display_name("NVDA") == "NVIDIA"
    assert r.display_name("tsmc") == "TSMC"
    assert r.display_name("AMD") == "AMD"               # unregistered: unchanged

# --- data home: docs/taxonomy.json consumed in place (spec decision 3) ---

def test_default_resolver_reads_repo_taxonomy():
    r = default_resolver()
    assert r.resolve("NVDA") == ("nvidia", True)
    assert r.resolve("Taiwan Semiconductor") == ("tsmc", True)
    assert default_resolver() is r                       # cached: one taxonomy read

def test_loader_tolerates_taxonomy_without_seed_entities(tmp_path):
    p = tmp_path / "tax.json"
    p.write_text(json.dumps({"layers": []}), "utf-8")
    r = EntityResolver.load(p)
    assert r.resolve("NVDA") == ("nvda", False)          # empty resolver = today's behavior
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && ../../.venv/Scripts/python -m pytest tests/test_entities.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'gpu_agent.entities'`.

- [ ] **Step 3: Implement** — `gpu_agent/entities.py`:

```python
"""F24 stage 1: canonical entity identity for NEW data. The single resolver over
docs/taxonomy.json `modularity.seedEntities` (consumed in place — no new registry file).
Known aliases (ticker, name variants, canonical id) resolve to the canonical id;
unregistered names return their slug form with registered=False and are NEVER rejected.
Deterministic: one cached taxonomy read, same input -> same output."""
from __future__ import annotations
import json
import pathlib
import re
from functools import lru_cache
from pydantic import BaseModel, Field

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug_key(name: str) -> str:
    """Slugified matching key: case-insensitive plus whitespace/punctuation-robust
    (same normalization rule as wiki.ingest.slug). Empty result fails loud."""
    s = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"unresolvable entity (empty slug): {name!r}")
    return s


class SeedEntity(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    primaryCategory: str
    appearsIn: list[str] = Field(default_factory=list)


class EntityResolver:
    def __init__(self, seeds: list[SeedEntity]):
        self._seeds_by_id: dict[str, SeedEntity] = {}
        self._alias_to_id: dict[str, str] = {}
        for seed in seeds:
            self._seeds_by_id[seed.id] = seed
            for variant in (seed.id, seed.name, *seed.aliases):
                key = _slug_key(variant)
                claimed = self._alias_to_id.get(key)
                if claimed is not None and claimed != seed.id:
                    raise ValueError(
                        f"entity alias collision: {variant!r} claimed by both "
                        f"'{claimed}' and '{seed.id}'")
                self._alias_to_id[key] = seed.id

    @classmethod
    def load(cls, path) -> "EntityResolver":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        raw = data.get("modularity", {}).get("seedEntities", [])
        return cls([SeedEntity.model_validate(e) for e in raw])

    def resolve(self, name: str) -> tuple[str, bool]:
        """(canonical_id, registered). Unregistered names return their slug form with
        False — pass-through, never a rejection (spec decision 2)."""
        key = _slug_key(name)
        canonical = self._alias_to_id.get(key)
        if canonical is not None:
            return canonical, True
        return key, False

    def display_name(self, name: str) -> str:
        canonical, registered = self.resolve(name)
        return self._seeds_by_id[canonical].name if registered else name

    def primary_category(self, name: str) -> str | None:
        canonical, registered = self.resolve(name)
        return self._seeds_by_id[canonical].primaryCategory if registered else None

    def appears_in(self, name: str) -> tuple[str, ...]:
        canonical, registered = self.resolve(name)
        return tuple(self._seeds_by_id[canonical].appearsIn) if registered else ()


@lru_cache(maxsize=1)
def default_resolver() -> EntityResolver:
    from gpu_agent.config import TAXONOMY_PATH
    return EntityResolver.load(TAXONOMY_PATH)
```

- [ ] **Step 4: Run to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_entities.py -q`
Expected: all pass.

- [ ] **Step 5: Full suite** — `../../.venv/Scripts/python -m pytest -q` — expected 1212 passed / 5 skipped (baseline 1200 + 12 new).

- [ ] **Step 6: Commit** (after `git log --oneline -1`):

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && git add gpu_agent/entities.py tests/test_entities.py && git commit -F - <<'EOF'
feat(entities): F24 stage-1 canonical entity resolver over taxonomy seedEntities

resolve() alias->canonical-id (slug-keyed, case-insensitive), display_name /
primary_category / appears_in accessors, cached default_resolver. Unregistered
names return slug form + registered=False (pass-through, never rejected).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 2: Seam A — normalize registered aliases at finding creation

**Files:**
- Modify: `gpu_agent/extraction/extractor.py` (the `extract_findings` draft loop + `ExtractionOutcome`)
- Test: `tests/test_extractor_entities.py` (new)

**Interfaces:**
- Consumes: `default_resolver()` from Task 1.
- Produces: `ExtractionOutcome.unregisteredEntities: list[str]` (sorted, distinct raw names). Consumed by Task 3 (CLI flag line).

- [ ] **Step 1: Write the failing tests** — `tests/test_extractor_entities.py`:

```python
"""F24 Seam A: a validated brain answer carrying a registered alias stores the finding
under the canonical id; unregistered names pass through UNCHANGED, flagged on the outcome
(user-approved Q2 2026-07-12). Uses the real repo taxonomy (nvidia/tsmc registered)."""
import json
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.extraction.extractor import extract_findings

def _doc():
    return RawDocument(id="doc-1", source="NVIDIA 10-Q", url="u", date="2026-05",
                       tier="primary", entity="nvidia", content="DC revenue grew 8% QoQ.")

def _draft(entity="NVDA", statement="DC growth flattened"):
    return {"statement": statement, "kind": "measured",
            "value": {"number": 8.0, "unit": "% QoQ"}, "trend": "rising", "why": "digestion",
            "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "caps DMI"},
            "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05-01", "excerpt": "8%"}],
            "confidence": {"level": "high", "basis": "filing"}, "indicatorId": "D2",
            "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
            "entity": entity, "observedAt": "2026-05-01"}

def _extract(*drafts):
    client = RecordedClient([json.dumps({"drafts": list(drafts)})])
    return extract_findings(_doc(), client, as_of="2026-06",
                            captured_at="2026-06-12T00:00:00Z",
                            extraction_model="claude-opus-4-8")

def test_registered_alias_stores_under_canonical_id():        # acceptance 2
    out = _extract(_draft(entity="NVDA"))
    assert len(out.findings) == 1 and not out.dropped
    assert out.findings[0].entity == "nvidia"
    assert out.unregisteredEntities == []

def test_canonical_id_passes_untouched():
    out = _extract(_draft(entity="nvidia"))
    assert out.findings[0].entity == "nvidia"
    assert out.unregisteredEntities == []

def test_unregistered_passes_through_unchanged_and_flagged():  # acceptance 4 (outcome half)
    out = _extract(_draft(entity="Super Micro"))
    assert len(out.findings) == 1 and not out.dropped          # NEVER rejected
    assert out.findings[0].entity == "Super Micro"             # NOT rewritten (Q2)
    assert out.unregisteredEntities == ["Super Micro"]

def test_unregistered_names_are_distinct_and_sorted():
    out = _extract(_draft(entity="Super Micro"),
                   _draft(entity="AMD", statement="MI400 ramps"),
                   _draft(entity="AMD", statement="MI400 pricing"))
    assert out.unregisteredEntities == ["AMD", "Super Micro"]

def test_registered_mixed_with_unregistered():
    out = _extract(_draft(entity="NVDA"), _draft(entity="AMD", statement="MI400 ramps"))
    assert [f.entity for f in out.findings] == ["nvidia", "AMD"]
    assert out.unregisteredEntities == ["AMD"]
```

- [ ] **Step 2: Run to verify failure**

Run: `../../.venv/Scripts/python -m pytest tests/test_extractor_entities.py -q`
Expected: FAIL — `out.findings[0].entity == "nvidia"` is `"NVDA"`, and `ExtractionOutcome` has no `unregisteredEntities`.

- [ ] **Step 3: Implement.** In `gpu_agent/extraction/extractor.py`:

(a) Extend `ExtractionOutcome` (NOT the frozen Finding schema — this model lives in extractor.py):

```python
class ExtractionOutcome(BaseModel):
    findings: list[Finding] = []
    dropped: list[DroppedFinding] = []
    # F24: distinct unregistered entity names seen this extraction (pass-through, flagged)
    unregisteredEntities: list[str] = []
```

(b) In `extract_findings`, after the taxonomy default block, add the resolver; inside the draft loop, immediately after `fid = f"{doc.id}-{i}"` (i.e. after brain-output validation, before gate/routing — the spec's Seam A pin):

```python
    from gpu_agent.entities import default_resolver
    resolver = default_resolver()
    ...
    unregistered: set[str] = set()
    for i, draft in enumerate(result.drafts, start=1):
        fid = f"{doc.id}-{i}"
        # F24 Seam A: registered aliases normalize to the canonical id; unregistered
        # names pass through UNCHANGED, flagged (user-approved Q2 2026-07-12). An
        # unsluggable name is treated as unregistered — never a rejection here.
        try:
            canonical, registered = resolver.resolve(draft.entity)
        except ValueError:
            canonical, registered = draft.entity, False
        if registered:
            if draft.entity != canonical:
                draft = draft.model_copy(update={"entity": canonical})
        else:
            unregistered.add(draft.entity)
```

(c) Return: `return ExtractionOutcome(findings=findings, dropped=dropped, unregisteredEntities=sorted(unregistered))`.

- [ ] **Step 4: Run to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_extractor_entities.py tests/test_extractor.py tests/test_extractor_v12.py tests/test_extraction_drafts.py -q`
Expected: all pass (`test_extraction_drafts` calls `draft_to_finding` directly — below the seam, still "NVDA").

- [ ] **Step 5: Full suite** — `../../.venv/Scripts/python -m pytest -q` — expected green (1217 passed / 5 skipped). Watch specifically: `test_pipeline.py`, `test_cli_extract.py`, `test_cli_pipeline_corpus.py`, `test_evals_*` (surveyed clean — none assert post-extraction entity values), and `test_evals_baseline_pin.py` (prompt bytes untouched).

- [ ] **Step 6: Commit** (after `git log --oneline -1`):

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && git add gpu_agent/extraction/extractor.py tests/test_extractor_entities.py && git commit -F - <<'EOF'
feat(extraction): F24 Seam A — canonical entity id at finding creation

Registered aliases (NVDA->nvidia) normalize immediately after brain-output
validation, before gate/routing. Unregistered names pass through unchanged and
land on ExtractionOutcome.unregisteredEntities (flag, never reject). No Finding
schema change; no emitted-prompt bytes.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 3: CLI flag line — `UNREGISTERED-ENTITY` on stderr (extract + pipeline)

**Files:**
- Modify: `gpu_agent/cli.py` (`_extract` ~line 313-341, `_pipeline` ~line 747-768)
- Test: `tests/test_cli_extract.py` (append two tests)

**Interfaces:**
- Consumes: `ExtractionOutcome.unregisteredEntities` from Task 2.
- Produces: stderr line `UNREGISTERED-ENTITY <n>: <names>` — the surface run-cycle Step 3(b) records into the journal (Task 5).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_cli_extract.py` (reuse its `_write_doc`; add a helper writing a recorded answer whose draft entity is `"AMD"` — copy `_recorded` and change `"entity": "NVDA"` to `"entity": "AMD"`, e.g. as `_recorded_amd(p)`):

```python
def test_extract_prints_unregistered_entity_line(tmp_path, capsys):
    docs = tmp_path / "docs"; docs.mkdir(); _write_doc(docs / "doc-1.json")
    rec = tmp_path / "rec.json"; _recorded_amd(rec)
    rc = main(["extract", "--docs", str(docs), "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--recorded", str(rec),
               "--out", str(tmp_path / "findings.json")])
    assert rc == 0
    assert "UNREGISTERED-ENTITY 1: AMD" in capsys.readouterr().err

def test_extract_no_unregistered_line_when_all_registered(tmp_path, capsys):
    docs = tmp_path / "docs"; docs.mkdir(); _write_doc(docs / "doc-1.json")
    rec = tmp_path / "rec.json"; _recorded(rec)                 # draft entity NVDA -> registered
    rc = main(["extract", "--docs", str(docs), "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--recorded", str(rec),
               "--out", str(tmp_path / "findings.json")])
    assert rc == 0
    assert "UNREGISTERED-ENTITY" not in capsys.readouterr().err
```

- [ ] **Step 2: Run to verify failure** — `../../.venv/Scripts/python -m pytest tests/test_cli_extract.py -q` — expected: first new test FAILS (no line printed).

- [ ] **Step 3: Implement.** In `_extract`, aggregate and print next to the DROPPED prints (same pattern):

```python
    all_findings, all_dropped = [], []
    unregistered: set[str] = set()
    for doc in docs:
        outcome = extract_findings(...)
        all_findings.extend(outcome.findings)
        all_dropped.extend(outcome.dropped)
        unregistered.update(outcome.unregisteredEntities)
    ...
    for d in all_dropped:
        print(f"DROPPED {d.id}: {'; '.join(d.violations)}", file=sys.stderr)
    if unregistered:
        names = sorted(unregistered)
        print(f"UNREGISTERED-ENTITY {len(names)}: {', '.join(names)}", file=sys.stderr)
```

Mirror the same three lines in `_pipeline` (its doc loop already collects `findings, dropped`; add the `unregistered` set and print immediately after its DROPPED loop, before the `gate dropped N` summary).

- [ ] **Step 4: Run to verify pass** — `../../.venv/Scripts/python -m pytest tests/test_cli_extract.py tests/test_pipeline_headline.py tests/test_cli_pipeline_corpus.py -q` — expected: all pass.

- [ ] **Step 5: Full suite** — `../../.venv/Scripts/python -m pytest -q` — expected green (1219 passed / 5 skipped).

- [ ] **Step 6: Commit** (after `git log --oneline -1`):

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && git add gpu_agent/cli.py tests/test_cli_extract.py && git commit -F - <<'EOF'
feat(cli): F24 UNREGISTERED-ENTITY stderr flag line in extract + pipeline

Per-cycle count + distinct names, DROPPED-pattern surface (user-approved Q3
2026-07-12, stderr half). Journal half rides run-cycle SKILL.md (next commit).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 4: Seam B — wiki entity-page keying + test migration

**Files:**
- Modify: `gpu_agent/wiki/ingest.py` (`_entity_page_id`, `route_findings` title)
- Test (new assertions): `tests/test_wiki_ingest_phase1.py`
- Migrate (surveyed list above): `tests/test_wiki_ingest_phase1.py`, `test_wiki_ingest_apply.py`, `test_wiki_ingest_cli.py`, `test_wiki_v12.py`, `test_brief_movement.py`, `test_brief_report.py`, `test_w2_lane_f.py`, `test_w2_lane_g.py`, `test_wiki_lint_materiality.py`, `test_wiki_lint_cli.py`

**Interfaces:**
- Consumes: `default_resolver()` from Task 1 (`resolve`, `display_name`).
- Produces: entity page ids derived from the canonical id for registered names; unchanged slug behavior for unregistered names.

- [ ] **Step 1: Write the failing tests** — add to `tests/test_wiki_ingest_phase1.py`:

```python
def test_route_alias_lands_on_canonical_entity_page(tmp_path):   # acceptance 3
    ws = _store(tmp_path)
    touched = route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    assert touched == ["entity:nvidia"]
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1"}
    assert ws.get_page("entity:nvidia").title == "NVIDIA"        # routed title = display name

def test_route_alias_and_canonical_share_one_page(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    touched = route_findings(ws, [_f("f-2", "nvidia")], as_of="2026-06-28")
    assert touched == ["entity:nvidia"]                          # no nvda-vs-nvidia split minted
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1", "f-2"}

def test_route_unregistered_entity_unchanged(tmp_path):
    ws = _store(tmp_path)
    touched = route_findings(ws, [_f("f-1", "Super Micro")], as_of="2026-06-28")
    assert touched == ["entity:super-micro"]                     # plain slug, as today
    assert ws.get_page("entity:super-micro").title == "Super Micro"
```

- [ ] **Step 2: Run to verify failure** — `../../.venv/Scripts/python -m pytest tests/test_wiki_ingest_phase1.py -q` — expected: the three new tests FAIL (`entity:nvda`, title `NVDA`).

- [ ] **Step 3: Implement.** In `gpu_agent/wiki/ingest.py`:

```python
from gpu_agent.entities import default_resolver

def _entity_page_id(finding: Finding) -> str:
    if not finding.entity or not finding.entity.strip():
        raise ValueError(f"finding {finding.id} has empty entity; cannot route")
    # F24 Seam B: page slug derives from the RESOLVED canonical id, so no new
    # alias-split pages (nvda vs nvidia) are ever minted. Unregistered names keep
    # today's plain slug. Existing split pages are untouched (stage 2).
    canonical, _registered = default_resolver().resolve(finding.entity)
    return f"entity:{canonical}"
```

and in `route_findings`, the create call uses the display name so routed titles are canonical:

```python
            store.create_page(pid, "entity", default_resolver().display_name(f.entity),
                              category=category, as_of=as_of)
```

(`slug()` itself is unchanged — it stays the generic slugifier `resolve()` falls back to for unregistered names, and `dedup.prior_vintage` keeps using it: post-Seam-A live findings are already canonical, so its lookups stay consistent.)

- [ ] **Step 4: Run to verify the new tests pass and see the expected migration breakage**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_ingest_phase1.py -q` (new tests pass; old `entity:nvda` asserts fail), then the full suite to enumerate actual breakage:
`../../.venv/Scripts/python -m pytest -q 2>&1 | tail -20`
Expected failures ONLY in the 10 surveyed files. A failure anywhere else = un-surveyed blast radius: stop and investigate before proceeding (systematic-debugging, and if it reopens a design decision, QUESTION-STOP per repo CLAUDE.md).

- [ ] **Step 5: Migrate the surveyed tests** — per file, mechanical rules (user-approved Q1):
  - `route_findings(..., "NVDA" ...)` call sites stay `"NVDA"` (they now exercise the resolver).
  - Assertions/lookups on pages that a ROUTED "NVDA"/"Nvidia" finding produced: `entity:nvda` → `entity:nvidia`; page file `nvda.md` → `nvidia.md`; expected routed page titles `"NVDA"` → `"NVIDIA"` (`test_brief_movement.py`: `assert "NVIDIA" in reg_titles`, `s.title == "NVIDIA"` — update the nearby comments to keep them true).
  - `ws.update_header(...)` / `ws.record_state(...)` / enrichment `pageId` values that TARGET a routed page: `entity:nvda` → `entity:nvidia`.
  - Manually-built `entity:nvda` pages (via `store.create_page`) and un-routed uses: UNTOUCHED.
  - AMD/INTC/SEEDCO etc. (unregistered): UNTOUCHED everywhere.
  - Bodies like `"## NVDA\n..."` in enrichment fixtures: leave the prose; only the `pageId` key must change (the F14 gate checks citations/numbers, not headings).

- [ ] **Step 6: Full suite green** — `../../.venv/Scripts/python -m pytest -q` — expected 1222 passed / 5 skipped, including `test_evals_baseline_pin.py`.

- [ ] **Step 7: Self-review the diff** — `git diff` — check: no `wiki/{log,store,lint,textscan,bench}.py` hunks, no schema/, no frozen-core files, migrations touch only the 10 surveyed files + ingest.py.

- [ ] **Step 8: Commit** (after `git log --oneline -1`):

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && git add gpu_agent/wiki/ingest.py tests/test_wiki_ingest_phase1.py tests/test_wiki_ingest_apply.py tests/test_wiki_ingest_cli.py tests/test_wiki_v12.py tests/test_brief_movement.py tests/test_brief_report.py tests/test_w2_lane_f.py tests/test_w2_lane_g.py tests/test_wiki_lint_materiality.py tests/test_wiki_lint_cli.py && git commit -F - <<'EOF'
feat(wiki): F24 Seam B — entity pages keyed by resolved canonical id

_entity_page_id resolves before slugging (NVDA routes to entity:nvidia titled
NVIDIA); unregistered names keep today's plain slug. Existing split pages
untouched (stage 2). Test migration per user-approved Q1 2026-07-12: routed
assertions swapped nvda->nvidia in the 10 surveyed files; manually-built
entity:nvda pages left alone.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 5: Durable journal record — run-cycle SKILL.md

**Files:**
- Modify: `.claude/skills/run-cycle/SKILL.md` (Step 3(b) after the extract-gate command block ~line 108; Step 6 enrichment list ~line 247-253)

**Interfaces:**
- Consumes: the Task 3 stderr line.
- Produces: the journal's per-category `unregisteredEntities` record (session-authored — the cycle log has no code writer; this is the endorsed F80-rationale wiring, no frozen surface involved).

- [ ] **Step 1: Edit Step 3(b).** After the `extract --recorded ... --out <work>/findings.json` block's `--captured-at` note, add:

```markdown
Record any `UNREGISTERED-ENTITY <n>: <names>` stderr line (F24): those names are not in
`docs/taxonomy.json` seedEntities — the findings still pass (flagged, never rejected), but the
count + names must land in this category's cycle-log entry at finalize (Step 6). No line = record
`{count: 0, names: []}`.
```

- [ ] **Step 2: Edit Step 6.** In the per-ready-category enrichment list (after "the corpus counts (store in-window / fresh new / update / duplicate)"), add:

```markdown
the F24 unregistered-entities record (`unregisteredEntities: {count, names}` from Step 3(b)'s
`UNREGISTERED-ENTITY` stderr line; `{count: 0, names: []}` when none printed),
```

- [ ] **Step 3: Verify** — the F74 tripwire (`tests/test_store_cycle_log_integrity.py`) only rejects a MISSING `asOf` or bare plan keys; an added key cannot turn it red. Run: `../../.venv/Scripts/python -m pytest tests/test_store_cycle_log_integrity.py -q` — expected pass (or skip if no store/cycle-log.json in this worktree).

- [ ] **Step 4: Commit** (after `git log --oneline -1`):

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f24-entities && git add .claude/skills/run-cycle/SKILL.md && git commit -F - <<'EOF'
docs(run-cycle): F24 journal record for unregistered entities

Durable half of the flag surface (user-approved Q3 2026-07-12, F80 rationale:
stderr-only warnings go unread). The journal is session-authored at finalize;
Step 3(b) captures the UNREGISTERED-ENTITY line, Step 6 lands count+names in
the category's cycle-log entry. No frozen code touched; F74 tripwire unaffected.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 6: Verification + sentinel + push

- [ ] **Step 1:** superpowers:verification-before-completion. Full suite from worktree root, fresh: `../../.venv/Scripts/python -m pytest -q` — read the ACTUAL final line; expected 1222 passed / 5 skipped.
- [ ] **Step 2:** Constraint audit against main: `git diff main --stat` — confirm ONLY: `gpu_agent/entities.py`, `gpu_agent/extraction/extractor.py`, `gpu_agent/cli.py`, `gpu_agent/wiki/ingest.py`, `.claude/skills/run-cycle/SKILL.md`, `docs/superpowers/plans/...`, and the 12 test files (2 new, 10 migrated). Any frozen-core / F25 / store/ path in the stat = fix before proceeding.
- [ ] **Step 3:** `git push -u origin f24-entity-resolver` (branch only — NEVER main).
- [ ] **Step 4:** Write the sentinel to the ROOT repo path `C:\Users\danie\random_for_fun\.superpowers\handoffs\f24-entities-DONE.md`: date, branch + commit list, suite status (exact counts), delivered list vs the spec's 6 acceptance items, merge notes (main-merge ordering vs F25: independent — no shared files), and note that stage 2 (historical consolidation) remains open by design. STOP before merge.

## Self-review (done at plan-writing time)

- Spec coverage: acceptance 1→Task 1, 2→Task 2, 3→Task 4, 4→Tasks 2+3+5, 5→Task 1, 6→every task + Task 6. Non-goals honored: no historical consolidation, no rejection mode, no prompt vocabulary, no new registry file, no cross-category dedup logic (accessors only).
- Placeholder scan: every code step carries the actual code; migration rules are enumerated per file with exact swap rules.
- Type consistency: `resolve -> tuple[str, bool]`, `unregisteredEntities: list[str]`, `display_name -> str` used identically in Tasks 1/2/3/4.
