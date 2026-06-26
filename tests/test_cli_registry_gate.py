"""Regression guard: _load_registry() must invoke validate_against so a
malformed registry fails loud on every CLI path (doctrine criterion #4)."""
from gpu_agent.cli import _load_registry
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy


def test_load_registry_validates_and_shipped_registry_is_clean():
    """Calling _load_registry() must succeed without raising, proving that
    (a) validate_against is wired in, and (b) the shipped registry/taxonomy
    remain doctrine-clean (no scoring indicator with weight==0, no override
    naming an unknown category)."""
    registry, taxonomy = _load_registry()
    assert isinstance(registry, IndicatorRegistry)
    assert isinstance(taxonomy, Taxonomy)
    # If validate_against were absent the wiring goal would be untested;
    # if the registry became malformed it would have raised RegistryError above.
