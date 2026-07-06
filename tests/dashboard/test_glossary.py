from gpu_agent.dashboard.glossary import (
    load_glossary, plain_label, term_swap, has_big_figure,
)

def test_glossary_loads_labels_and_prose_terms():
    g = load_glossary()
    assert g["labels"]["DMI"] == "Demand momentum"
    assert "HBM" in g["prose_terms"]

def test_plain_label_falls_back_to_term_when_unknown():
    g = load_glossary()
    assert plain_label("DMI", g) == "Demand momentum"
    assert plain_label("Totally Unknown", g) == "Totally Unknown"

def test_term_swap_expands_jargon_case_insensitively_and_longest_first():
    g = {"labels": {}, "prose_terms": {"HBM": "high-bandwidth memory",
                                       "merchant-GPU": "open-market GPUs"}}
    out = term_swap("hbm demand for merchant-GPU rose", g)
    assert "high-bandwidth memory" in out
    assert "open-market GPUs" in out
    assert "HBM" not in out and "merchant-GPU" not in out

def test_has_big_figure_detects_dollars_billions_and_large_counts():
    assert has_big_figure("books over $2B China revenue")
    assert has_big_figure("underwriting well over 200,000 GPUs")
    assert has_big_figure("$1.5 billion committed")
    assert not has_big_figure("a small qualitative shift")
