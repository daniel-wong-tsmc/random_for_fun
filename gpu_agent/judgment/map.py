from __future__ import annotations

# indicatorId -> scorecard dimension (code default; YAGNI — not yet assignment-driven)
DIMENSION_MAP: dict[str, str] = {
    "D2": "momentum",
    "D6": "momentum",
    "grossMargin": "unitEconomics",
    "S9": "competitiveStructure",
    "S10": "bottleneck",
    "market-share-pct": "moat",
}

# dimension -> which polarity track expresses its signal (demand|supply)
DIMENSION_POLARITY: dict[str, str] = {
    "momentum": "demand",
    "unitEconomics": "demand",
    "competitiveStructure": "supply",
    "bottleneck": "supply",
    "moat": "demand",
    "strategicRisk": "supply",
}
