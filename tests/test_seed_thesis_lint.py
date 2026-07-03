"""F54 — seed thesis triggers must pass the observable heuristic they are judged under.

Born from the 2026-07-03 integration gate: two committed seed triggers named no
observable under thesis.py's v1 heuristic, so a brain echoing them back verbatim was
correctly rejected and had to reword — one avoidable re-dispatch per cycle. This lint
locks every seed trigger (and the depth fields) to gate-passing form.
"""
import json
import pathlib

import pytest

from gpu_agent.config import REGISTRY_PATH
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.thesis import _trigger_names_observable

SEED_PATH = "registry/theses.chips.merchant-gpu.json"
_THESES = json.loads(pathlib.Path(SEED_PATH).read_text(encoding="utf-8"))["theses"]


@pytest.mark.parametrize("thesis", _THESES, ids=[t["id"] for t in _THESES])
def test_seed_trigger_names_an_observable(thesis):
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    assert _trigger_names_observable(thesis["falsifiableTrigger"], registry), (
        f"{thesis['id']}: falsifiableTrigger names no observable under the v1 heuristic "
        f"(needs a registered indicator id, a digit, or a cadence word): "
        f"{thesis['falsifiableTrigger']!r}"
    )


@pytest.mark.parametrize("thesis", _THESES, ids=[t["id"] for t in _THESES])
def test_seed_depth_fields_non_empty(thesis):
    # mirrors gate rule 3's non-empty depth-field checks on the seed DATA
    assert thesis["statement"].strip()
    assert thesis["mechanism"].strip()
    assert thesis["sensitivity"].strip()
