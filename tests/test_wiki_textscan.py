import random
from gpu_agent.wiki.textscan import MultiSubstringMatcher


def test_single_match():
    m = MultiSubstringMatcher(["AMD"])
    assert m.matches("Competes with AMD on GPUs") == {"AMD"}


def test_absent():
    m = MultiSubstringMatcher(["AMD", "Intel"])
    assert m.matches("only nvidia here") == set()


def test_nested_substring_both_reported():
    # "AMD" is a substring of "AMD Instinct"; a body with the long one must report BOTH
    m = MultiSubstringMatcher(["AMD", "AMD Instinct"])
    assert m.matches("the AMD Instinct MI300") == {"AMD", "AMD Instinct"}


def test_overlapping_and_multiple():
    m = MultiSubstringMatcher(["aba", "bab"])
    assert m.matches("ababa") == {"aba", "bab"}


def test_empty_patterns_dropped():
    m = MultiSubstringMatcher(["", "x"])
    assert m.matches("xyz") == {"x"}


def test_property_matches_naive_oracle():
    rng = random.Random(1234)
    alpha = "abc"
    for _ in range(300):
        patterns = list({"".join(rng.choice(alpha) for _ in range(rng.randint(1, 4)))
                         for _ in range(rng.randint(1, 6))})
        text = "".join(rng.choice(alpha + " ") for _ in range(rng.randint(0, 30)))
        got = MultiSubstringMatcher(patterns).matches(text)
        want = {p for p in patterns if p and p in text}
        assert got == want, (patterns, text, got, want)
