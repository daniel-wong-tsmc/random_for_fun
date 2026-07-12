"""F80 tripwire: every wiki page must carry a non-null category.

Born 2026-07-12: store/wiki/entity/{nvidia,multi}.md carried ``category: null``
since F62, so ``enumerate_store``'s category filter silently excluded them from
every corpus — NVIDIA contributed zero store findings to its own category.
The pages were repaired by hand with user sign-off (F80); this test makes any
recurrence fail the suite loudly instead of surfacing only as SKIPPED-PAGE
stderr lines nobody reads.
"""

import pathlib
import re

WIKI_DIR = pathlib.Path(__file__).resolve().parents[1] / "store" / "wiki"

_NULLISH = {"null", '""', "''", ""}


def _front_matter_category(text: str):
    match = re.search(r"^category:\s*(.*)$", text, re.MULTILINE)
    if match is None:
        return None
    return match.group(1).strip()


def test_every_wiki_page_has_a_category():
    pages = sorted(WIKI_DIR.rglob("*.md"))
    assert pages, f"no wiki pages found under {WIKI_DIR}"
    offenders = []
    for page in pages:
        value = _front_matter_category(page.read_text("utf-8"))
        if value is None or value in _NULLISH:
            offenders.append(str(page.relative_to(WIKI_DIR)))
    assert not offenders, (
        "wiki pages with null/missing category are excluded from every corpus "
        f"(F80): {offenders}"
    )
