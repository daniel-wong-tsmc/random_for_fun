import re, pathlib
HANDOFF = pathlib.Path(__file__).resolve().parents[1] / "docs/superpowers/HANDOFF.md"

def _text():
    return HANDOFF.read_text("utf-8")

def test_single_current_state_block():
    # exactly one top-of-file resume-point line; everything else is HISTORICAL
    assert len(re.findall(r"resume point:", _text())) == 1

def test_provenance_labels_controlled():
    allowed = {"user-approved", "AFK-precedent", "AFK-default"}
    # forbidden phrasings that the F76b finding calls out as ambiguous
    forbidden = re.findall(r"user-decided|approved \(AFK\)|user-approved \(AFK", _text())
    assert forbidden == []

def test_retained_worktrees_registry_present():
    assert "## RETAINED WORKTREES REGISTRY" in _text()
