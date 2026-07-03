# F67 Output Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the rendered category report an exec-readable inverted pyramid (spec: `docs/superpowers/specs/2026-07-03-output-contract-design.md`) — fixed section order with an appendix fold, a reader-contract vocabulary layer (label map + acronym allowlist + lint), an additive-optional `constraintLabel`, analyst-voice + stop-slop rules in the judgment prompt, and a session-output rule in the run-cycle skill.

**Architecture:** A new `gpu_agent/reader.py` module owns all exec-facing vocabulary (label maps, acronym allowlist from `registry/acronyms.json`, prose lint). `report.py`/`brief.py` renderers consume it and reorder into BLUF → moved → calls → why → board → footer → `── APPENDIX ──`. The judgment prompt gains the voice rules and `constraintLabel`; the CLI judge path lints brain prose and fails loud (the session re-dispatches once, per the run-cycle skill edit). Everything stays a pure LLM-free projection.

**Tech Stack:** Python 3.12 + pydantic (existing), pytest, no new dependencies.

## Global Constraints

- The renderer is a pure projection: no LLM, no network, no clock reads except injected `render_ts` (report.py module docstring — keep true).
- Frozen contract: `gate.py`, `scoring.py`, Finding schema untouched. `CategoryStatus.constraintLabel` is **additive-optional** (`Optional[str] = None`) — absent field must render byte-identical behavior minus the new line.
- Reader contract (spec §2a): no indicator ids, finding ids, index acronyms (DMI/SMI/SDGI/PMI), or tier/status jargon ("primary"/"secondary"/"grounded"/"under-supported"/"provisional") above the `── APPENDIX ──` divider. All-caps tokens above the divider must be on the acronym allowlist.
- Narrative = exactly 3 sentences; dimension rationale ≤ 2 sentences (prompt + lint).
- Every task: run its new tests AND `python -m pytest -q` (full suite, baseline 828 passed / 3 skipped) before commit.
- Work happens on branch `feat/f67-output-contract` in a worktree (another session is active on main). Commands below assume repo root as cwd and `.venv/Scripts/python` on Windows.

---

### Task 1: Reader module + acronym allowlist data

**Files:**
- Create: `registry/acronyms.json`
- Create: `gpu_agent/reader.py`
- Test: `tests/test_reader.py`

**Interfaces:**
- Produces: `reader.TIER_LABEL: dict[str,str]`, `reader.STATUS_LABEL: dict[str,str]`, `reader.indicator_label(indicator_id, registry) -> str`, `reader.split_sentences(text) -> list[str]`, `reader.lint_prose(text, field, *, max_sentences=None) -> list[str]`, `reader.lint_acronyms(text) -> list[str]`, `reader.APPENDIX_DIVIDER: str`.
- Consumes: `IndicatorRegistry` (existing, `gpu_agent/registry/indicators.py`) — `registry.indicators[id].get("label")`.

- [ ] **Step 1: Write the allowlist data file**

`registry/acronyms.json` (industry-standard only — spec §2a):

```json
{
  "allowed": [
    "AI", "GPU", "CPU", "TPU", "ASIC", "HBM", "HBM3E", "HBM4", "COWOS",
    "SEC", "IR", "PR", "YOY", "QOQ", "FY", "Q1", "Q2", "Q3", "Q4",
    "10-Q", "10-K", "8-K", "CAPEX", "R&D", "US", "USD", "GB", "GW", "MW",
    "NVIDIA", "AMD", "INTEL", "TSMC", "OPENAI", "META", "GOOGLE", "MICROSOFT",
    "AWS", "NVL72", "MI450", "MI400", "H100", "H200", "B200", "GB200", "DGX",
    "BIS", "NOW", "NEXT", "NEW", "UP", "DOWN", "FLAT", "WATCH", "CHANGED", "MOVED",
    "INTACT", "CHALLENGED", "BROKEN", "STATE", "OF", "THE", "MARKET", "WHAT",
    "SINCE", "LAST", "RUN", "CALLS", "WHY", "DEMAND", "SUPPLY", "TRUST",
    "COVERAGE", "APPENDIX", "ACCELERATING", "SOFTENING", "CONTRACTING",
    "STEADY", "TIGHT", "BINDING", "CONSTRAINT", "CATEGORY", "REPORT"
  ]
}
```

(Uppercase section-header words and band words are listed so the acronym lint can stay a dumb all-caps scan. Vendor names and part numbers are industry-known. Extend the list, never the lint.)

- [ ] **Step 2: Write the failing tests**

`tests/test_reader.py`:

```python
"""Reader-contract layer (F67 spec §2a): label maps, acronym allowlist, prose lint."""
from gpu_agent import reader
from gpu_agent.registry.indicators import IndicatorRegistry

REG = IndicatorRegistry.load("registry/indicators.json")


def test_tier_and_status_labels():
    assert reader.TIER_LABEL["primary"] == "company filing / official post"
    assert reader.TIER_LABEL["secondary"] == "press / analyst report"
    assert reader.STATUS_LABEL["grounded"] == "well-evidenced"
    assert reader.STATUS_LABEL["under-supported"] == "thin evidence"
    assert reader.STATUS_LABEL["provisional"] == "early — not yet corroborated"


def test_indicator_label_prefers_registry_label():
    assert reader.indicator_label("rpoBacklog", REG) != "rpoBacklog"
    # unregistered id falls back to the id itself — never crashes
    assert reader.indicator_label("no-such-id", REG) == "no-such-id"


def test_split_sentences_handles_decimals_and_abbrev():
    text = "Revenue hit $75.2 billion in Q1. Growth was 92% YoY. Watch the next 10-Q."
    assert len(reader.split_sentences(text)) == 3


def test_lint_prose_flags_ids_and_sentence_cap():
    bad = "D2 rose sharply. rpoBacklog is strong. See www-sec-gov-125b52f2-2. More. And more."
    errs = reader.lint_prose(bad, "narrative", max_sentences=3)
    assert any("indicator id" in e for e in errs)          # D2 / rpoBacklog
    assert any("finding id" in e for e in errs)            # www-sec-gov-125b52f2-2
    assert any("sentence" in e for e in errs)              # 5 > 3


def test_lint_prose_flags_banned_words():
    errs = reader.lint_prose("We delve into a robust landscape.", "rationale")
    assert len([e for e in errs if "banned word" in e]) == 3


def test_lint_prose_clean_text_passes():
    good = ("Demand is strong because hyperscaler orders exceed packaging output. "
            "The crux is whether CoWoS capacity doubles by Q4. "
            "Watch TSMC lead times first.")
    assert reader.lint_prose(good, "narrative", max_sentences=3) == []


def test_lint_acronyms_uses_allowlist():
    assert reader.lint_acronyms("CoWoS and HBM3E are tight") == []
    errs = reader.lint_acronyms("SDGI is demand-led and PMI is flat")
    assert sorted(errs) == ["PMI", "SDGI"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_reader.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.reader'`

- [ ] **Step 4: Implement `gpu_agent/reader.py`**

```python
"""gpu_agent/reader.py — the F67 reader contract (spec §2a).

One home for every exec-facing vocabulary rule: the reader is a TSMC executive
with zero knowledge of this repo. Label maps translate internal jargon; the
acronym allowlist (registry/acronyms.json — DATA, edit there) bounds all-caps
tokens; lint_prose enforces the analyst-voice rules on brain-written fields.
Pure functions, no LLM, no network."""
from __future__ import annotations
import json
import re
from pathlib import Path

APPENDIX_DIVIDER = "──────────────────────────── APPENDIX ────────────────────────────"

TIER_LABEL = {
    "primary": "company filing / official post",
    "secondary": "press / analyst report",
}
STATUS_LABEL = {
    "grounded": "well-evidenced",
    "under-supported": "thin evidence",
    "provisional": "early — not yet corroborated",
}

# Brain-prose ban list (spec §2a + stop-slop's filler subset — deterministic slice only).
BANNED_WORDS = (
    "delve", "delves", "crucial", "pivotal", "robust", "landscape",
    "leverage", "leverages", "holistic", "seamless", "utilize", "utilizes",
)
# Finding ids look like `<slug>-<8 hex>-<n>` (see gathering ids in store/findings/).
_FINDING_ID_RE = re.compile(r"\b[a-z0-9][a-z0-9-]*-[0-9a-f]{8}-\d+\b")
_ALLCAPS_RE = re.compile(r"\b[A-Z][A-Z0-9&-]{1,}\b")
# Sentence split: end punctuation followed by whitespace+capital; decimals survive.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'0-9])")

_ACRONYMS_PATH = Path("registry/acronyms.json")
_INDICATOR_IDS: frozenset[str] | None = None
_ALLOWED: frozenset[str] | None = None


def _allowed() -> frozenset[str]:
    global _ALLOWED
    if _ALLOWED is None:
        _ALLOWED = frozenset(json.loads(_ACRONYMS_PATH.read_text("utf-8"))["allowed"])
    return _ALLOWED


def _indicator_ids() -> frozenset[str]:
    global _INDICATOR_IDS
    if _INDICATOR_IDS is None:
        raw = json.loads(Path("registry/indicators.json").read_text("utf-8"))
        _INDICATOR_IDS = frozenset(raw.get("indicators", {}))
    return _INDICATOR_IDS


def indicator_label(indicator_id: str, registry) -> str:
    """Human label for an indicator id; falls back to the id (never crashes)."""
    spec = registry.indicators.get(indicator_id) if registry is not None else None
    if isinstance(spec, dict):
        return spec.get("label") or indicator_id
    return indicator_id


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    return [s for s in _SENT_SPLIT_RE.split(text) if s.strip()]


def lint_acronyms(text: str) -> list[str]:
    """All-caps tokens not on the allowlist (spec §2a) — sorted, deduplicated."""
    allowed = _allowed()
    hits = {t for t in _ALLCAPS_RE.findall(text or "")
            if t.upper() not in allowed and t not in allowed}
    return sorted(hits)


def lint_prose(text: str, field: str, *, max_sentences: int | None = None) -> list[str]:
    """Analyst-voice lint for one brain-written field. Returns violations (empty = clean).
    Checks: indicator ids, finding ids, banned words, sentence cap, off-list acronyms."""
    errs: list[str] = []
    text = text or ""
    lowered = text.lower()
    tokens = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text))
    for ind in sorted(_indicator_ids() & tokens):
        errs.append(f"{field}: indicator id '{ind}' in exec-facing prose")
    for m in sorted(set(_FINDING_ID_RE.findall(lowered))):
        errs.append(f"{field}: finding id '{m}' in exec-facing prose")
    for w in BANNED_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", lowered):
            errs.append(f"{field}: banned word '{w}'")
    if max_sentences is not None:
        n = len(split_sentences(text))
        if n > max_sentences:
            errs.append(f"{field}: {n} sentences (max {max_sentences})")
    for a in lint_acronyms(text):
        errs.append(f"{field}: acronym '{a}' not on registry/acronyms.json allowlist")
    return errs
```

Note: `lint_prose` flagging `rpoBacklog` works because indicator ids are matched as whole tokens against the registry key set — camelCase ids need no special regex.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_reader.py -q`
Expected: 7 passed. Iterate on the sentence-split / allowlist details until green — the test file is the contract.

- [ ] **Step 6: Full suite, then commit**

Run: `.venv/Scripts/python -m pytest -q` — expected: baseline count + 7 new, 0 failures.

```bash
git add registry/acronyms.json gpu_agent/reader.py tests/test_reader.py
git commit -m "feat(f67): reader-contract module - label maps, acronym allowlist, prose lint"
```

---

### Task 2: `constraintLabel` schema field + judgment prompt voice rules

**Files:**
- Modify: `gpu_agent/schema/scorecard.py:22-26` (CategoryStatus)
- Modify: `gpu_agent/judgment/prompt.py:6-29` (_SYSTEM_TEMPLATE)
- Modify: whichever test pins the SYSTEM template (find it: `grep -rn "SYSTEM" tests/test_cli_emit_prompt.py tests/test_judge*.py tests/test_cli_persona.py`)
- Test: `tests/test_constraint_label.py`

**Interfaces:**
- Produces: `CategoryStatus.constraintLabel: Optional[str] = None`; the judgment answer JSON may now include `"categoryStatus": {..., "constraintLabel": "..."}`.
- Consumes: nothing new.

- [ ] **Step 1: Write the failing test**

`tests/test_constraint_label.py`:

```python
"""F67: additive-optional CategoryStatus.constraintLabel."""
import json
from gpu_agent.schema.scorecard import CategoryStatus
from gpu_agent.judgment import prompt as jprompt


def test_constraint_label_optional_roundtrip():
    cs = CategoryStatus(rating="Strong", direction="improving",
                        bottleneck="bottleneck", reason="r")
    assert cs.constraintLabel is None          # absent → None, old payloads valid
    cs2 = CategoryStatus(rating="Strong", direction="improving",
                         bottleneck="bottleneck", reason="r",
                         constraintLabel="CoWoS/HBM3E advanced packaging")
    assert "CoWoS" in cs2.constraintLabel
    assert "constraintLabel" in json.loads(cs2.model_dump_json())


def test_system_prompt_carries_voice_rules_and_constraint_label():
    sys = jprompt.build_system()
    assert "constraintLabel" in sys
    assert "exactly three sentences" in sys        # narrative rule
    assert "at most two sentences" in sys          # rationale rule
    assert "active voice" in sys                   # stop-slop core
    assert "TSMC executive" in sys                 # reader contract
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_constraint_label.py -q`
Expected: FAIL (`constraintLabel` unexpected kwarg; assertions on template).

- [ ] **Step 3: Implement**

In `gpu_agent/schema/scorecard.py`, CategoryStatus becomes:

```python
class CategoryStatus(BaseModel):
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]
    direction: Literal["improving", "steady", "worsening"]
    bottleneck: str
    reason: str
    # F67 (additive-optional): plain-language name of the physical/market constraint,
    # e.g. "CoWoS/HBM3E advanced packaging" — never a dimension name. The renderer
    # omits the BLUF constraint line when absent; nothing downstream requires it.
    constraintLabel: Optional[str] = None
```

In `gpu_agent/judgment/prompt.py`, extend `_SYSTEM_TEMPLATE`. After the existing
categoryStatus paragraph (ends "...binding constraint right now (the bottleneck).") add:

```text
Also set categoryStatus.constraintLabel: a plain-language name (at most 6 words) for the
concrete physical or market constraint, e.g. "CoWoS/HBM3E advanced packaging" — NEVER a
dimension name and never the word "bottleneck".

VOICE (binding — a deterministic lint rejects violations): the reader is a TSMC executive
with no knowledge of this system. The narrative is exactly three sentences: (1) the state
and why now; (2) the crux — the one or two questions that decide the next rating change;
(3) the watch item — what would most likely change this picture and where it would show
first. Each dimension rationale is at most two sentences and names the deciding evidence,
not a list of everything. Write in active voice with concrete nouns. Never use indicator
ids (D2, S10, rpoBacklog), finding ids, index acronyms (DMI, SMI, SDGI, PMI), or the
words delve/crucial/pivotal/robust/landscape. No "not X but Y" constructions. Avoid
hedged pairs ("strong but risks remain") unless the same sentence says which side wins
and why.
```

Update the JSON shape line in the template from
`"categoryStatus": {"rating","direction","bottleneck","reason"}` to
`"categoryStatus": {"rating","direction","bottleneck","reason","constraintLabel"}`.

- [ ] **Step 4: Fix the pinned-SYSTEM test**

`gpu_agent/judgment/prompt.py:34` says the SYSTEM constant is pinned by a test. Find it:
`grep -rln "byte-identical\|build_system()" tests/ | xargs grep -ln "SYSTEM"`. Update that
test's expectation to the new template (assert on the new stable substrings — e.g.
`"constraintLabel" in SYSTEM` — rather than a full literal, so future template edits
don't re-break it; keep any persona-substitution assertions as-is).

- [ ] **Step 5: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_constraint_label.py tests/test_cli_emit_prompt.py tests/test_cli_persona.py tests/test_judge*.py -q` — expected: all pass.
Then full suite: `.venv/Scripts/python -m pytest -q` — expected: green.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/schema/scorecard.py gpu_agent/judgment/prompt.py tests/
git commit -m "feat(f67): constraintLabel (additive-optional) + analyst-voice rules in judgment prompt"
```

---

### Task 3: Voice lint on the judge recorded path (fail loud, session re-dispatches)

**Files:**
- Modify: `gpu_agent/cli.py` — the `judge` handler's `--recorded` branch (find: `grep -n "_judge\|def _judge\|recorded" gpu_agent/cli.py`)
- Test: `tests/test_judge_voice_lint.py`

**Interfaces:**
- Consumes: `reader.lint_prose` (Task 1); the parsed judge answer (narrative, per-dimension rationale, categoryStatus.reason, constraintLabel).
- Produces: exit code 1 + one `voice-lint:` line per violation on stderr when the recorded answer violates the voice rules; `--no-voice-lint` flag to bypass (recorded legacy fixtures).

- [ ] **Step 1: Write the failing test**

`tests/test_judge_voice_lint.py` — follow the subprocess conventions of
`tests/test_cli_judge.py` (copy its `_run` helper and fixture-loading pattern; build a
minimal recorded judge answer inline in tmp_path):

```python
"""F67: the judge --recorded path lints brain prose and fails loud."""
import json, os, subprocess, sys

def _run(*args):
    env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True, encoding="utf-8", env=env, cwd=".")

BAD_NARRATIVE = "D2 rose. SDGI is robust. One. Two. Five sentences now."
GOOD_NARRATIVE = ("Demand is strong because hyperscaler orders exceed packaging output. "
                  "The crux is whether CoWoS capacity doubles by Q4. "
                  "Watch TSMC lead times first.")

def _answer(narrative):
    # Reuse the committed recorded fixture and override only the narrative,
    # so dimensions/citations stay gate-valid.
    base = json.load(open("fixtures/recorded/judge-nvda.json", encoding="utf-8"))
    base["narrative"] = narrative
    return base

def test_bad_prose_fails_loud(tmp_path):
    p = tmp_path / "ans.json"; p.write_text(json.dumps(_answer(BAD_NARRATIVE)), "utf-8")
    r = _run("judge", "--recorded", str(p), "--findings", "fixtures/golden/findings.json")
    assert r.returncode != 0
    assert "voice-lint:" in r.stderr

def test_good_prose_passes(tmp_path):
    p = tmp_path / "ans.json"; p.write_text(json.dumps(_answer(GOOD_NARRATIVE)), "utf-8")
    r = _run("judge", "--recorded", str(p), "--findings", "fixtures/golden/findings.json")
    assert r.returncode == 0

def test_bypass_flag(tmp_path):
    p = tmp_path / "ans.json"; p.write_text(json.dumps(_answer(BAD_NARRATIVE)), "utf-8")
    r = _run("judge", "--recorded", str(p), "--findings", "fixtures/golden/findings.json",
             "--no-voice-lint")
    assert r.returncode == 0
```

Adapt the exact `judge` CLI arguments to what `tests/test_cli_judge.py` actually passes
(read it first — the flag names above are placeholders for the real ones; keep the three
behaviors: fail-loud, pass, bypass).

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_judge_voice_lint.py -q`
Expected: FAIL — no lint, all return 0 / unknown `--no-voice-lint` flag.

- [ ] **Step 3: Implement in `gpu_agent/cli.py`**

In the judge subparser add `--no-voice-lint` (`action="store_true"`,
help "skip the F67 analyst-voice lint (legacy recorded fixtures)").
In the recorded-answer handling, after the answer JSON is parsed and BEFORE the existing
judgment gate/apply, add:

```python
if not args.no_voice_lint:
    from gpu_agent import reader
    violations: list[str] = []
    violations += reader.lint_prose(answer.get("narrative", ""), "narrative", max_sentences=3)
    for dim, d in (answer.get("dimensions") or {}).items():
        violations += reader.lint_prose(d.get("rationale", ""), f"{dim}.rationale", max_sentences=2)
    cs = answer.get("categoryStatus") or {}
    violations += reader.lint_prose(cs.get("reason", ""), "categoryStatus.reason")
    label = cs.get("constraintLabel")
    if label:
        from gpu_agent.schema.scorecard import DIMENSIONS
        if label in DIMENSIONS or "bottleneck" in label.lower():
            violations.append("categoryStatus.constraintLabel: must name the concrete "
                              "constraint, not a dimension")
        if len(label.split()) > 6:
            violations.append("categoryStatus.constraintLabel: over 6 words")
    if violations:
        for v in violations:
            print(f"voice-lint: {v}", file=sys.stderr)
        return 1
```

(Adapt variable names to the handler's actual locals. The session-side rule — re-dispatch
the judge subagent once with the violation lines, then fail the stage — is Task 9's skill
edit; code only fails loud.)

- [ ] **Step 4: Run tests; fix legacy fixtures fallout**

Run: `.venv/Scripts/python -m pytest tests/test_judge_voice_lint.py tests/test_cli_judge.py -q`.
If committed recorded fixtures (`fixtures/recorded/judge-nvda.json`) now fail the lint in
existing tests, add `--no-voice-lint` to THOSE test invocations (they test the gate, not
the voice) — do not rewrite the fixtures.

- [ ] **Step 5: Full suite, commit**

```bash
.venv/Scripts/python -m pytest -q
git add gpu_agent/cli.py tests/
git commit -m "feat(f67): analyst-voice lint on judge --recorded, fail-loud with bypass flag"
```

---

### Task 4: Header staleness banner + honest confidence label

**Files:**
- Modify: `gpu_agent/report.py:127-135` (render_header) and `render_report` (pass sc)
- Test: `tests/test_report_banner.py`

**Interfaces:**
- Produces: `render_header(sc, render_ts) -> str` now includes an evidence-vintage line and a relabeled confidence line. New helper `evidence_vintage(sc) -> tuple[str|None, str|None, float]` (median date, oldest date, share older than 42 days vs asOf).
- Consumes: `sc.findings[].evidence[].date` (ISO strings), `sc.confidence` (`level`, `basis`), `sc.asOf` (month `YYYY-MM` or day grain).

- [ ] **Step 1: Write the failing test**

`tests/test_report_banner.py`:

```python
"""F67 banner: evidence vintage + honest confidence label in the header."""
from gpu_agent.report import load_scorecard, render_header, evidence_vintage

SC = load_scorecard("fixtures/report/postb-scorecard.json")


def test_evidence_vintage_math():
    median, oldest, stale_share = evidence_vintage(SC)
    assert median is not None and oldest is not None
    assert oldest <= median
    assert 0.0 <= stale_share <= 1.0


def test_header_carries_banner_and_relabeled_confidence():
    out = render_header(SC, "2026-07-03T00:00:00+00:00")
    assert "Evidence:" in out                      # vintage line
    assert "vote agreement" in out                 # confidence relabel
    assert "self-consistency" not in out           # jargon gone
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_report_banner.py -q`
Expected: FAIL — `evidence_vintage` not defined; header lacks lines.

- [ ] **Step 3: Implement in `report.py`**

```python
def _as_of_date(as_of: str) -> str:
    return f"{as_of}-01" if len(as_of) == 7 else as_of


def evidence_vintage(sc: Scorecard):
    """(median_date, oldest_date, share_older_than_42d) over all evidence dates.
    Pure string/date math; no clock. Empty findings -> (None, None, 0.0)."""
    from datetime import date
    dates = sorted(ev.date for f in sc.findings for ev in f.evidence if ev.date)
    if not dates:
        return None, None, 0.0
    median = dates[len(dates) // 2]
    cutoff = date.fromisoformat(_as_of_date(sc.asOf)).toordinal() - 42
    stale = sum(1 for d in dates if date.fromisoformat(d).toordinal() < cutoff)
    return median, dates[0], stale / len(dates)
```

`render_header(sc, render_ts)` (keep the signature — it already takes sc) appends after
the bar:

```python
    median, oldest, stale_share = evidence_vintage(sc)
    lines = [bar, title, bar]
    if median is not None:
        lines.append(f" Evidence: median {median} · oldest {oldest} · "
                     f"{round(stale_share * 100)}% older than 6 weeks")
    basis = sc.confidence.basis or ""
    m = re.search(r"(\d+)", basis)
    votes = f" ({m.group(1)} votes)" if m else ""
    lines.append(f" Confidence: vote agreement {sc.confidence.level}{votes} — "
                 f"agreement between raters, not evidence freshness")
    return "\n".join(lines)
```

(Check the actual `Confidence` model field name for `basis` in `gpu_agent/schema/finding.py`
first; adapt if it differs.)

- [ ] **Step 4: Run tests, fix existing header expectations**

Run: `.venv/Scripts/python -m pytest tests/test_report_banner.py tests/test_cli_report.py tests/test_brief_report.py -q`.
Update any test asserting the exact old 3-line header.

- [ ] **Step 5: Full suite, commit**

```bash
.venv/Scripts/python -m pytest -q
git add gpu_agent/report.py tests/
git commit -m "feat(f67): header staleness banner + vote-agreement confidence label"
```

---

### Task 5: BLUF — constraint noun, reconciliation note, kill the duplicate paragraph

**Files:**
- Modify: `gpu_agent/brief.py:20-73` (render_state_of_market)
- Modify: `gpu_agent/report.py:138-172` (render_overall_status)
- Test: `tests/test_brief_state.py` (extend), `tests/test_report_no_duplicate.py`

**Interfaces:**
- Consumes: `CategoryStatus.constraintLabel` (Task 2).
- Produces: BLUF constraint line `BINDING CONSTRAINT: <constraintLabel>` only when the label exists; a deterministic reconciliation note; `render_overall_status` no longer repeats `reason`.

- [ ] **Step 1: Write the failing tests**

Extend `tests/test_brief_state.py` (append; follow its existing fixture-building style —
read the file first and reuse its scorecard factory):

```python
def test_constraint_line_uses_label_never_dimension(sc_factory):
    sc = sc_factory(category_status={"rating": "Strong", "direction": "improving",
                                     "bottleneck": "bottleneck", "reason": "r",
                                     "constraintLabel": "CoWoS/HBM3E advanced packaging"})
    out = brief.render_state_of_market(sc, None)
    assert "BINDING CONSTRAINT: CoWoS/HBM3E advanced packaging" in out

def test_constraint_line_omitted_without_label(sc_factory):
    sc = sc_factory(category_status={"rating": "Strong", "direction": "improving",
                                     "bottleneck": "bottleneck", "reason": "r"})
    out = brief.render_state_of_market(sc, None)
    assert "BINDING CONSTRAINT" not in out          # honest omission, no jargon leak

def test_reconciliation_note_when_strong_but_supply_negative(sc_factory):
    sc = sc_factory(rating="Strong", smi=-0.45)
    out = brief.render_state_of_market(sc, None)
    assert "supply is the constraint" in out
```

New `tests/test_report_no_duplicate.py`:

```python
"""F67: the status reason renders exactly once in the whole report."""
from gpu_agent.report import load_scorecard, render_report
from gpu_agent.registry.indicators import IndicatorRegistry

def test_reason_appears_once():
    sc = load_scorecard("fixtures/report/postb-scorecard.json")
    out = render_report(sc, None, IndicatorRegistry.load("registry/indicators.json"),
                        render_ts="2026-07-03T00:00:00+00:00")
    assert out.count(sc.categoryStatus.reason) == 1
```

- [ ] **Step 2: Run to verify they fail** — `pytest tests/test_brief_state.py tests/test_report_no_duplicate.py -q` → FAIL.

- [ ] **Step 3: Implement**

In `brief.render_state_of_market` replace the final constraint block (`lines 71-72`):

```python
    if cs is not None and getattr(cs, "constraintLabel", None):
        lines.append(f"  BINDING CONSTRAINT: {cs.constraintLabel}")
```

After the Gap line, add the reconciliation note (deterministic, data-derived):

```python
    if (cs is not None and cs.rating in ("Strong", "Very strong")
            and ds.smiContribution < 0):
        lines.append("  Note: the supply reading is negative because supply is the "
                     "constraint — a demand-led shortage, not a demand problem.")
```

In `report.render_overall_status`, replace the `Reason:` line with
`"  Reason:     see State of the Market above"` when `sc.categoryStatus` is present
(keep the legacy-absent branch untouched).

- [ ] **Step 4: Run tests, update fallout** — `test_brief_state.py`, `test_cli_report.py` (any "BINDING CONSTRAINT: bottleneck" or Reason assertions). Expected: green after updates.

- [ ] **Step 5: Full suite, commit**

```bash
.venv/Scripts/python -m pytest -q
git add gpu_agent/brief.py gpu_agent/report.py tests/
git commit -m "feat(f67): BLUF names the real constraint, reconciliation note, single reason paragraph"
```

---

### Task 6: THE CALLS + WHY — statements not excerpts, cite counts not id dumps

**Files:**
- Modify: `gpu_agent/brief.py:263-377` (_calls_headline_line, _calls_evidence_line, render_the_calls) and `brief.py:399-518` (_why_finding_suffix)
- Test: `tests/test_brief_calls.py`, `tests/test_brief_why.py` (extend/update)

**Interfaces:**
- Produces: calls evidence line = `      <thesis statement>  (<N> sources: <tier words>)`; WHY suffix = `  (<N> sources)` or `  (sources in history)`. `_calls_evidence_line(entry, finding_ids, findings_by_id)` — note it now takes the entry (for `entry.statement`).
- Consumes: `reader.TIER_LABEL`, `reader.STATUS_LABEL` (Task 1); `ThesisBook` entries' `statement` field (exists — see `store/theses/.../book.json`).

- [ ] **Step 1: Write the failing tests** (extend the two test files; reuse their book/scorecard factories — read them first):

```python
def test_calls_line_uses_thesis_statement_and_source_counts(book_factory, sc_factory):
    out = brief.render_the_calls(book, sc, {"t1": ["f-1", "f-2", "f-3"]})
    assert "3 sources" in out
    assert "[" not in out.split("breaks if")[0]     # no id dumps anywhere in the block
    assert book.entries[0].statement[:40] in out    # full statement, not an excerpt

def test_calls_provisional_renders_reader_label(book_factory, sc_factory):
    out = brief.render_the_calls(book_prov, sc, None)
    assert "(early — not yet corroborated)" in out
    assert "(provisional)" not in out

def test_why_suffix_is_counts_not_ids(book_factory):
    out = brief.render_why(book, {"t1": ["f-1", "f-2"]})
    assert "(2 sources)" in out
    assert "f-1" not in out
```

- [ ] **Step 2: Run to verify they fail** — expected FAIL on all three.

- [ ] **Step 3: Implement**

`_calls_headline_line`: replace the `prov` suffix with
`prov = f"  ({reader.STATUS_LABEL['provisional']})" if entry.status == "provisional" else ""`
(import `from gpu_agent import reader` at brief.py top).

`_calls_evidence_line(entry, finding_ids, findings_by_id)`:

```python
def _calls_evidence_line(entry, finding_ids, findings_by_id) -> str:
    """Second line: the thesis's own statement + a source-count tag (reader contract —
    ids live in the appendix citation map, never here)."""
    if not finding_ids:
        return f"      {entry.statement}  (sources in history)"
    resolved = [findings_by_id[fid] for fid in finding_ids if fid in findings_by_id]
    n = len(finding_ids)
    if resolved and any(ev.tier == "primary" for f in resolved for ev in f.evidence):
        tier = f", incl. {reader.TIER_LABEL['primary']}"
    else:
        tier = ""
    return f"      {entry.statement}  ({n} source{'s' if n != 1 else ''}{tier})"
```

Update the caller in `render_the_calls` accordingly. `_why_finding_suffix`:

```python
def _why_finding_suffix(entry_id, last_findings) -> str:
    ids = (last_findings or {}).get(entry_id)
    if ids:
        return f"  ({len(ids)} source{'s' if len(ids) != 1 else ''})"
    return "  (sources in history)"
```

Remove `_CALLS_STATEMENT_CAP` truncation (the statement is one authored sentence, no cap;
delete the constant if now unused).

- [ ] **Step 4: Run tests + update all existing expectations in `test_brief_calls.py` / `test_brief_why.py`** (they assert the old id-dump format extensively). Expected: green after updates.

- [ ] **Step 5: Full suite, commit**

```bash
.venv/Scripts/python -m pytest -q
git add gpu_agent/brief.py tests/
git commit -m "feat(f67): calls/why speak thesis statements and source counts, ids move to appendix"
```

---

### Task 7: Demand|Supply board — human labels, reader-worded tags

**Files:**
- Modify: `gpu_agent/brief.py:100-139` (_board_rows, render_demand_supply_board)
- Modify: `gpu_agent/report.py` render_report call site (pass registry)
- Test: `tests/test_brief_board.py` (extend)

**Interfaces:**
- Produces: `render_demand_supply_board(sc, horizons, registry=None) -> str` — rows read `    <label>  <word> <arrow>  [tags]` with `reader.indicator_label`; `⚠carried` becomes `⚠ from a prior cycle`; `⚠single-source` becomes `⚠ one source`.
- Consumes: `reader.indicator_label` (Task 1); `IndicatorRegistry` from render_report (already loaded there).

- [ ] **Step 1: Write the failing test** (extend `tests/test_brief_board.py`, reusing its factories):

```python
def test_board_rows_use_registry_labels(sc_factory):
    reg = IndicatorRegistry.load("registry/indicators.json")
    out = brief.render_demand_supply_board(sc, horizons=None, registry=reg)
    assert "Backlog" in out or "Guidance" in out    # labels from registry
    assert "rpoBacklog" not in out
    assert " D2 " not in out
    assert "⚠ one source" in out
    assert "single-source" not in out
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** — `_board_rows(findings, side, sc_as_of, horizons, registry)`:
row line becomes `f"    {reader.indicator_label(indicator_id, registry):<24}  {word} {arrow}{suffix}"`;
tag strings: `"⚠ from a prior cycle"` (was `⚠carried`), `"⚠ one source"` (was `⚠single-source`),
`"leading"` stays (plain English). `render_demand_supply_board` gains `registry=None`
keyword and threads it; `report.render_report` passes its `registry`.

- [ ] **Step 4: Run tests + update old board expectations.** Expected: green.

- [ ] **Step 5: Full suite, commit**

```bash
.venv/Scripts/python -m pytest -q
git add gpu_agent/brief.py gpu_agent/report.py tests/
git commit -m "feat(f67): board rows speak registry labels and plain-word flags"
```

---

### Task 8: Section reorder + APPENDIX divider + dead-metric fold + daily lead + contract tests

**Files:**
- Modify: `gpu_agent/report.py:607-670` (render_report), `report.py:341-365` (render_price_track)
- Modify: `gpu_agent/cli.py` report subparser (add `--daily`)
- Test: `tests/test_report_contract.py`

**Interfaces:**
- Produces: `render_report(..., daily: bool = False)`; section order (standard):
  header → state → what-moved → calls → why → board → storylines → trust footer →
  `reader.APPENDIX_DIVIDER` → overall status → dimensions → price track → entity panel →
  evidence quality → sources → coverage gaps. Daily: what-moved renders immediately after
  header, before state. CLI: `gpu_agent.cli report --daily` threads the flag.
- Consumes: `reader.APPENDIX_DIVIDER`, everything from Tasks 4–7.

- [ ] **Step 1: Write the failing tests**

`tests/test_report_contract.py`:

```python
"""F67 output-contract integration tests over committed fixtures (no store/, no LLM)."""
import json
from gpu_agent import reader
from gpu_agent.report import load_scorecard, render_report
from gpu_agent.registry.indicators import IndicatorRegistry

REG = IndicatorRegistry.load("registry/indicators.json")
SC = load_scorecard("fixtures/report/postb-scorecard.json")
TS = "2026-07-03T00:00:00+00:00"


def _above_appendix(out: str) -> str:
    assert reader.APPENDIX_DIVIDER in out
    return out.split(reader.APPENDIX_DIVIDER)[0]


def test_section_order_standard():
    out = render_report(SC, None, REG, render_ts=TS)
    order = ["STATE OF THE MARKET", "WHAT MOVED", "THE CALLS", "WHY",
             "DEMAND | SUPPLY", "TRUST & COVERAGE", reader.APPENDIX_DIVIDER,
             "OVERALL CATEGORY STATUS", "DIMENSION RATINGS"]
    idx = [out.index(s) for s in order]
    assert idx == sorted(idx)


def test_daily_leads_with_what_moved():
    out = render_report(SC, None, REG, render_ts=TS, daily=True)
    assert out.index("WHAT MOVED") < out.index("STATE OF THE MARKET")


def test_no_jargon_above_appendix():
    top = _above_appendix(render_report(SC, None, REG, render_ts=TS))
    for banned in ("under-supported", "grounded", "(provisional)",
                   "single-source", "PMI", "SDGI", "DMI", "SMI"):
        assert banned not in top, banned
    assert reader.lint_acronyms(top) == []


def test_dead_price_metrics_fold():
    # postb fixture has no matched prior series -> the fold line, not dash rows
    out = render_report(SC, None, REG, render_ts=TS)
    assert "Δ vs prior: —" not in out
    if "PRICE TRACK" in out:
        assert "needs two matched cycles" in out


def test_empty_state_lines_are_honest():
    out = render_report(SC, None, REG, render_ts=TS)   # no movement passed
    assert "(no wiki store yet" in out or "no prior cycle" in out
    assert "\n  (none)\n" not in _above_appendix(out)
```

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement**

`render_report` gains `daily: bool = False`; sections list becomes (comment each move):

```python
    top = [
        render_header(sc, render_ts),
        brief.render_state_of_market(sc, prior, track),
        brief.render_what_moved(movement),
        brief.render_the_calls(thesis_book, sc, thesis_last_findings),
        brief.render_why(thesis_book, thesis_last_findings),
        brief.render_demand_supply_board(sc, horizons, registry=registry),
        brief.render_storylines(movement),
        render_trust_footer(sc, prior),
    ]
    if daily:   # F67 §4: the daily's headline is the diff
        top[1], top[2] = top[2], top[1]
    appendix = [
        reader.APPENDIX_DIVIDER,
        render_overall_status(sc),
        render_dimensions(sc, prior),
        render_price_track(track),
        render_entity_panel(sc),
        render_evidence_quality(sc, registry),
        render_sources(sc),
        render_coverage_gaps(sc),
    ]
    return "\n\n".join(s for s in top + appendix if s)
```

`render_price_track`: when every `s.delta is None` and `track.pmi is None`, return the
fold line
`f"PRICE TRACK\n  {len(track.series)} price series captured; day-over-day change needs two matched cycles"`
instead of per-series dash rows. (Matched-prior case keeps the detailed rows.)

`brief.render_state_of_market`: drop the `Price overlay: … PMI` line entirely (the price
story lives in the appendix; PMI is off-allowlist above the divider).

CLI: add `--daily` to the report subparser, thread to `render_report(daily=args.daily)`.

STORYLINES above the divider: change `_storyline_group_lines` empty-group return from
`["    (none)"]` to `["    (none tracked yet)"]` and group titles
`"REGISTERED (canonical)"` → `"ESTABLISHED"`, `"PROVISIONAL (confidence-capped)"` →
`"EARLY (not yet corroborated)"` — reader words.

- [ ] **Step 4: Run the new tests + the full brief/report test files; update ordering/wording expectations** (`tests/test_cli_report.py` SECTION_HEADERS list, `test_brief_storylines.py`, `test_brief_report.py`). Expected: green after updates.

- [ ] **Step 5: Full suite, commit**

```bash
.venv/Scripts/python -m pytest -q
git add gpu_agent/report.py gpu_agent/brief.py gpu_agent/cli.py tests/
git commit -m "feat(f67): inverted-pyramid section order, appendix fold, dead-metric fold, --daily lead"
```

---

### Task 9: Skill edits + live render check

**Files:**
- Modify: `.claude/skills/run-cycle/SKILL.md` (report step ~line 146, daily step ~line 215)
- Test: manual render (this task has no pytest surface; the deliverable is skill text + a verified live render)

**Interfaces:**
- Consumes: `report --daily` (Task 8), voice lint exit behavior (Task 3).

- [ ] **Step 1: Edit the report step (f)** — after the existing render command paragraph, add:

```markdown
**Session-output rule (F67).** The session's FINAL message for a cycle is the rendered
report VERBATIM plus at most three run-health lines (docs gathered/kept, dedup
new/update/duplicate, caps tripped or stages failed). Reference gather logs, prompts,
and dedup detail by file path only — never paste them. Before sending, apply the
stop-slop skill's rules to any prose the session itself writes around the report (the
report text is deterministic and must not be edited).
```

- [ ] **Step 2: Edit the judge step** — where the skill describes dispatching judge
subagents, add:

```markdown
If `judge --recorded` exits non-zero with `voice-lint:` lines, re-dispatch the judgment
subagent ONCE with those lines appended to its prompt ("fix these violations; change
nothing else"). If it fails the lint again, run `judge --recorded ... --no-voice-lint`,
log `voice-lint: bypassed` in the cycle log, and continue — the lint never blocks a
scorecard, it only demands one rewrite attempt.
```

- [ ] **Step 3: Edit the daily step (report-daily)** — change the render command to pass
`--daily` and note "the daily brief leads with WHAT MOVED (F67 §4)".

- [ ] **Step 4: Live render check (read-only)**

Run: `.venv/Scripts/python -m gpu_agent.cli report --scorecard store/chips.merchant-gpu/2026-07-v1.json --store store`
Verify by eye against the spec: BLUF first, no id dumps above the appendix, banner
present, one reason paragraph, price fold. Then run
`.venv/Scripts/python -m pytest -q` one final time (expected: green, ~860+ passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/run-cycle/SKILL.md
git commit -m "feat(f67): session-output rule, voice-lint re-dispatch rule, --daily render in run-cycle skill"
```

---

## Self-review notes (spec coverage)

- Spec §1 rows 1–9 → Tasks 4 (header), 5 (BLUF), 8 (order/fold/daily), 6 (calls/why), 7 (board). Row 7 (TSMC slot) is intentionally a no-op: the section renders nothing until F65 — no code needed beyond the ordering comment.
- Spec §2a (reader contract) → Tasks 1, 6, 7, 8 (label map + allowlist + above-appendix tests); §2b (depth rules) → Task 2 (prompt) + Task 3 (lint).
- Spec §3 (session rule) + re-dispatch semantics → Task 9.
- Spec §4 (daily shell) → Task 8 (`--daily`) + Task 9 step 3. F64's trigger-watch stays out of scope per spec.
- Spec "Testing" section → test_report_contract.py (order, jargon, acronyms, fold, empty-state), test_report_no_duplicate.py, test_reader.py (lint), Task 3 (re-dispatch path is skill-side; code path tested as fail-loud + bypass).
- Known deviation, recorded: the spec's banner mentions a not-covered-source count; that data lives in gather-log.json, not the scorecard, so the banner ships vintage + confidence only and the coverage story stays in the appendix COVERAGE section. Revisit if a `--gather-log` argument is ever justified (YAGNI now).
