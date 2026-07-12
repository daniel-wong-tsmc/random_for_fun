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


# --- F24 stage 2 (spec 2026-07-13): the v2.0-era registrations the six F79 series cite ---
# Every ticker and common press form of each registered entity resolves to its canonical id
# against the REAL repo taxonomy (default_resolver). Aliases cover tickers (NVDA-style) and
# common press handles ("Google", "AWS", "Foxconn"-style) per the spec.

_STAGE2_ALIASES = [
    # merchant vendors (own chips.merchant-gpu)
    ("AMD", "amd"), ("amd", "amd"), ("Advanced Micro Devices", "amd"),
    ("Intel", "intel"), ("INTC", "intel"), ("Intel Corporation", "intel"),
    ("Broadcom", "broadcom"), ("AVGO", "broadcom"), ("Broadcom Inc", "broadcom"),
    # hyperscaler buyers (appearsIn merchant-gpu; own hyperscale-cloud)
    ("Microsoft", "microsoft"), ("MSFT", "microsoft"), ("Microsoft Corporation", "microsoft"),
    ("Microsoft Azure", "microsoft"), ("Azure", "microsoft"),
    ("Alphabet", "alphabet"), ("GOOGL", "alphabet"), ("GOOG", "alphabet"),
    ("Google", "alphabet"), ("Google Cloud", "alphabet"),
    ("Amazon", "amazon"), ("AMZN", "amazon"), ("AWS", "amazon"),
    ("Amazon Web Services", "amazon"), ("Amazon.com", "amazon"),
    ("Meta", "meta"), ("META", "meta"), ("Meta Platforms", "meta"), ("Facebook", "meta"),
    ("Oracle", "oracle"), ("ORCL", "oracle"), ("Oracle Corporation", "oracle"),
    ("Oracle Cloud", "oracle"), ("OCI", "oracle"),
    # memory (appearsIn merchant-gpu; own hbm-memory)
    ("SK Hynix", "sk-hynix"), ("SK hynix", "sk-hynix"), ("Hynix", "sk-hynix"),
    ("Samsung", "samsung"), ("Samsung Electronics", "samsung"),
    ("Micron", "micron"), ("MU", "micron"), ("Micron Technology", "micron"),
    # neoclouds (appearsIn merchant-gpu; own neocloud)
    ("CoreWeave", "coreweave"), ("CRWV", "coreweave"),
    ("Lambda Labs", "lambda-labs"), ("Lambda", "lambda-labs"), ("Lambda Cloud", "lambda-labs"),
]


@pytest.mark.parametrize("alias,canonical", _STAGE2_ALIASES)
def test_stage2_alias_resolves_to_canonical(alias, canonical):
    assert default_resolver().resolve(alias) == (canonical, True), alias


# primaryCategory per the spec's lane-discipline table.
_STAGE2_PRIMARY = {
    "amd": "chips.merchant-gpu", "intel": "chips.merchant-gpu", "broadcom": "chips.merchant-gpu",
    "microsoft": "infrastructure.hyperscale-cloud", "alphabet": "infrastructure.hyperscale-cloud",
    "amazon": "infrastructure.hyperscale-cloud", "meta": "infrastructure.hyperscale-cloud",
    "oracle": "infrastructure.hyperscale-cloud",
    "sk-hynix": "chips.hbm-memory", "samsung": "chips.hbm-memory", "micron": "chips.hbm-memory",
    "coreweave": "infrastructure.neocloud", "lambda-labs": "infrastructure.neocloud",
}


@pytest.mark.parametrize("cid,primary", sorted(_STAGE2_PRIMARY.items()))
def test_stage2_primary_category(cid, primary):
    assert default_resolver().primary_category(cid) == primary, cid


def test_stage2_only_merchant_vendors_own_merchant_gpu():
    """Lane discipline (charter Part 21 'counted once'): chips.merchant-gpu is the
    primaryCategory of ONLY the merchant vendors; every hyperscaler / memory / neocloud
    buyer merely appearsIn it, so cross-category rollups count each entity once."""
    r = default_resolver()
    owners = {cid for cid, primary in _STAGE2_PRIMARY.items()
              if primary == "chips.merchant-gpu"}
    assert owners == {"amd", "intel", "broadcom"}
    for cid, primary in _STAGE2_PRIMARY.items():
        if cid in owners:
            continue
        assert primary != "chips.merchant-gpu", cid
        assert "chips.merchant-gpu" in r.appears_in(cid), cid


def test_stage2_display_names_are_taxonomy_truth():
    r = default_resolver()
    assert r.display_name("AVGO") == "Broadcom"
    assert r.display_name("Google") == "Alphabet"
    assert r.display_name("AWS") == "Amazon"
    assert r.display_name("Foxconn") == "Foxconn"           # ODM: not yet registered (spec fork)


def test_stage2_registrations_load_without_alias_collision():
    """The whole registered set loads (default_resolver would raise on any alias claimed by
    two ids), and the two pre-existing seeds are untouched."""
    r = default_resolver()
    assert r.resolve("NVDA") == ("nvidia", True)
    assert r.resolve("Taiwan Semiconductor") == ("tsmc", True)
