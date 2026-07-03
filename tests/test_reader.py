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
