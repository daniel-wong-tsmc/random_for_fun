"""F24 stage 1 — the entity resolver (spec 2026-07-12). Acceptance 1 (alias resolution)
and 5 (primaryCategory/appearsIn accessors return taxonomy truth)."""
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
