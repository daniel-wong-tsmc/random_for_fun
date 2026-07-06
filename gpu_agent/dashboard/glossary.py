import json
import re
from pathlib import Path

_DEFAULT = Path(__file__).with_name("glossary.json")


def load_glossary(path=None):
    p = Path(path) if path else _DEFAULT
    with open(p, encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    data.setdefault("labels", {})
    data.setdefault("prose_terms", {})
    return data


def plain_label(term, glossary):
    return glossary.get("labels", {}).get(term, term)


def term_swap(text, glossary):
    if not text:
        return text
    terms = sorted(glossary.get("prose_terms", {}), key=len, reverse=True)
    out = text
    for term in terms:
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        out = pattern.sub(glossary["prose_terms"][term], out)
    return out


_MONEY = re.compile(r"\$\s?\d", re.IGNORECASE)
_BILLIONS = re.compile(r"\b\d[\d,.]*\s?(?:billion|bn)\b", re.IGNORECASE)
_BIG_COUNT = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{6,}\b")


def has_big_figure(text):
    if not text:
        return False
    return bool(_MONEY.search(text) or _BILLIONS.search(text) or _BIG_COUNT.search(text))
