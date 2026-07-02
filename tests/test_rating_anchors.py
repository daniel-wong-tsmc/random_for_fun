"""Structure guard for docs/rating-anchors.md (F39).

Keeps the rating-anchor doc from drifting into decoration: every dimension
must be defined, every rating word must appear exactly once per dimension as
a table row, the bottleneck/strategicRisk inversion must be stated
explicitly, and the doc must stay category-agnostic outside a clearly-marked
Examples block.
"""

import pathlib
import re

import pytest

DOC = pathlib.Path("docs/rating-anchors.md")

DIMENSIONS = [
    "momentum",
    "unitEconomics",
    "competitiveStructure",
    "moat",
    "bottleneck",
    "strategicRisk",
]

INVERTED_DIMENSIONS = ["bottleneck", "strategicRisk"]

RATINGS = ["Very strong", "Strong", "Mixed", "Weak", "Very weak"]

INVERSION_PHRASE = "presence of the factor"


def _text():
    assert DOC.exists(), f"{DOC} is missing"
    return DOC.read_text(encoding="utf-8")


def _sections(text):
    """Split the doc into {heading_text: body_text} on '## ' (H2) headings."""
    parts = re.split(r"(?m)^## ", text)
    sections = {}
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        sections[heading.strip()] = body
    return sections


def _section_body_for_dimension(sections, dim_id):
    for heading, body in sections.items():
        if f"`{dim_id}`" in heading:
            return body
    raise AssertionError(f"no '## ' heading found carrying dimension id `{dim_id}`")


def test_doc_exists():
    _text()


def test_all_six_dimension_ids_appear_as_headings():
    sections = _sections(_text())
    missing = [d for d in DIMENSIONS if not any(f"`{d}`" in h for h in sections)]
    assert not missing, f"missing heading(s) for dimension id(s): {missing}"


@pytest.mark.parametrize("dim_id", DIMENSIONS)
def test_each_dimension_section_has_all_five_ratings_exactly_once(dim_id):
    body = _section_body_for_dimension(_sections(_text()), dim_id)
    for rating in RATINGS:
        row_pattern = re.compile(rf"(?m)^\|\s*{re.escape(rating)}\s*\|")
        matches = row_pattern.findall(body)
        assert len(matches) == 1, (
            f"dimension `{dim_id}` expected exactly one table row for rating "
            f"{rating!r}, found {len(matches)}"
        )


@pytest.mark.parametrize("dim_id", INVERTED_DIMENSIONS)
def test_inversion_note_present_for_bottleneck_and_strategic_risk(dim_id):
    body = _section_body_for_dimension(_sections(_text()), dim_id)
    assert INVERSION_PHRASE in body, (
        f"dimension `{dim_id}` must state the inversion explicitly "
        f"(expected the pinned phrase {INVERSION_PHRASE!r})"
    )


def test_non_inverted_dimensions_do_not_carry_the_inversion_phrase():
    sections = _sections(_text())
    for dim_id in DIMENSIONS:
        if dim_id in INVERTED_DIMENSIONS:
            continue
        body = _section_body_for_dimension(sections, dim_id)
        assert INVERSION_PHRASE not in body, (
            f"dimension `{dim_id}` is not one of {INVERTED_DIMENSIONS}; "
            "the inversion phrasing belongs only to bottleneck/strategicRisk"
        )


def test_examples_block_exists_and_is_clearly_marked():
    sections = _sections(_text())
    examples_headings = [h for h in sections if h.lower().startswith("examples")]
    assert examples_headings, "doc must have a clearly-marked '## Examples' section"


def test_no_gpu_outside_the_examples_block():
    text = _text()
    sections = _sections(text)
    examples_headings = [h for h in sections if h.lower().startswith("examples")]
    assert examples_headings, "doc must have a clearly-marked '## Examples' section"

    # Rebuild the doc with the Examples section(s) removed, then check for "GPU".
    non_example_text = text
    for heading in examples_headings:
        # Remove from the heading line through to the next H2 heading (or EOF).
        pattern = re.compile(
            rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)"
        )
        non_example_text = pattern.sub("", non_example_text)

    assert "GPU" not in non_example_text, (
        "'GPU' must only appear inside the clearly-marked Examples section"
    )


def test_gpu_actually_used_inside_examples_to_prove_the_guard_is_meaningful():
    sections = _sections(_text())
    examples_heading = next(h for h in sections if h.lower().startswith("examples"))
    assert "GPU" in sections[examples_heading]
