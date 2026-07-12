"""F23 - charter compliance matrix lint.

Parses docs/compliance-matrix.md and fails if the matrix is internally
inconsistent or references anything that does not exist. Pure stdlib - no
product imports - so it cannot be contaminated by product-code changes.

The matrix maps every binding charter clause to its enforcement point and
pinning test. This lint stops the map from rotting silently (the F23 goal:
keep 'binding' from drifting into aspiration - would have caught F2/F3/F5).
"""
import re
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/compliance-matrix.md"
CHARTER = ROOT / "docs/agent-swarm-charter.md"

COLUMNS = ["Clause ID", "Part", "Clause", "Status", "Enforcement", "Pinning test"]
SUMMARY_COLUMNS = ["Status", "Count"]
STATUSES = {"ENFORCED", "PARTIAL", "SESSION-PROSE", "DEFERRED", "NOT-ENFORCED", "NARRATIVE"}

# a repo-root-relative path token, e.g. gpu_agent/gate.py, registry/x.json,
# .claude/skills/run-cycle/SKILL.md  (optional ::symbol suffix)
_PATH_RE = re.compile(r"[.\w][\w./-]*\.(?:py|json|md|toml|cmd)(?:::\w+)?")
_CLAUSE_ID_RE = re.compile(r"^P(\d+)(?:\.[\w-]+)?$")
_LINENO_RE = re.compile(r"\.py:\d+")


def _cells(line):
    # a table row: strip leading/trailing pipe, split on '|', trim cells
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [c.strip() for c in inner.split("|")]


def _is_separator(cells):
    return all(set(c) <= set("-: ") and c for c in cells)


def _table_after(header_cells):
    """Return the list of data-row cell-lists for the single table whose header
    equals header_cells. Fails if not exactly one such header exists."""
    lines = MATRIX.read_text(encoding="utf-8").splitlines()
    starts = [i for i, ln in enumerate(lines)
              if ln.lstrip().startswith("|") and _cells(ln) == header_cells]
    assert len(starts) == 1, (
        f"expected exactly one table with header {header_cells}, found {len(starts)}")
    rows = []
    i = starts[0] + 1
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = _cells(lines[i])
        if not _is_separator(cells):
            rows.append(cells)
        i += 1
    return rows


def _matrix_rows():
    return _table_after(COLUMNS)


def _summary_counts():
    out = {}
    for cells in _table_after(SUMMARY_COLUMNS):
        assert len(cells) == 2, f"summary row not 2 cells: {cells}"
        out[cells[0]] = int(cells[1])
    return out


def _charter_parts():
    text = CHARTER.read_text(encoding="utf-8")
    return sorted({int(m) for m in re.findall(r"^## Part (\d+)", text, re.M)})


# ---- the checks -----------------------------------------------------------

def test_matrix_file_exists():
    assert MATRIX.is_file(), f"{MATRIX} missing"


def test_rows_have_six_cells():
    for cells in _matrix_rows():
        assert len(cells) == len(COLUMNS), f"row not {len(COLUMNS)} cells: {cells}"


def test_clause_ids_wellformed_unique_and_match_part():
    charter_parts = set(_charter_parts())   # derived live, so a future Part 40 just works
    seen = set()
    for cells in _matrix_rows():
        cid, part = cells[0], cells[1]
        m = _CLAUSE_ID_RE.match(cid)
        assert m, f"bad Clause ID: {cid!r}"
        assert cid not in seen, f"duplicate Clause ID: {cid}"
        seen.add(cid)
        assert part.isdigit(), f"Part not an int: {part!r} ({cid})"
        assert int(m.group(1)) == int(part), f"Clause ID {cid} disagrees with Part {part}"
        assert int(part) in charter_parts, f"Part {part} is not a charter Part ({cid})"


def test_status_vocabulary_controlled():
    for cells in _matrix_rows():
        assert cells[3] in STATUSES, f"bad Status {cells[3]!r} in {cells[0]}"


def test_no_line_numbers_anywhere():
    for cells in _matrix_rows():
        for c in cells:
            assert not _LINENO_RE.search(c), f"line-number ref in {cells[0]}: {c!r}"


def test_every_charter_part_present():
    parts_in_matrix = {int(cells[1]) for cells in _matrix_rows()}
    missing = [p for p in _charter_parts() if p not in parts_in_matrix]
    assert not missing, f"charter Parts with no matrix row: {missing}"


def test_referenced_paths_exist():
    for cells in _matrix_rows():
        for col in (cells[4], cells[5]):        # Enforcement, Pinning test
            for tok in _PATH_RE.findall(col):
                path_part = tok.split("::", 1)[0]
                assert (ROOT / path_part).is_file(), (
                    f"{cells[0]}: referenced path does not exist: {path_part}")


def test_referenced_test_functions_exist():
    for cells in _matrix_rows():
        for col in (cells[4], cells[5]):
            for tok in _PATH_RE.findall(col):
                if "::" not in tok:
                    continue
                path_part, sym = tok.split("::", 1)
                body = (ROOT / path_part).read_text(encoding="utf-8")
                assert re.search(rf"def {re.escape(sym)}\b", body), (
                    f"{cells[0]}: {sym} not defined in {path_part}")


def test_enforced_rows_name_a_pinning_test():
    # An ENFORCED claim without a test is exactly the rot this matrix exists to
    # catch: the row must cite at least one tests/ path (file or file::function).
    for cells in _matrix_rows():
        if cells[3] != "ENFORCED":
            continue
        pins = [t for t in _PATH_RE.findall(cells[5]) if t.startswith("tests/")]
        assert pins, f"{cells[0]}: ENFORCED but Pinning-test cell names no tests/ path: {cells[5]!r}"


def test_summary_counts_match_rows():
    rows = _matrix_rows()
    actual = Counter(cells[3] for cells in rows)
    summary = _summary_counts()
    for status in STATUSES:
        assert summary.get(status, 0) == actual.get(status, 0), (
            f"summary {status}={summary.get(status, 0)} but rows have {actual.get(status, 0)}")
    assert set(summary) <= STATUSES, f"summary lists unknown status: {set(summary) - STATUSES}"
    assert sum(summary.values()) == len(rows), "summary total != row count"
