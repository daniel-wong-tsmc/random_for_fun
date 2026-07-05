from __future__ import annotations
import os
from functools import lru_cache

# F42: hardcoded registry/taxonomy paths, centralized and env-overridable. Defaults are
# byte-identical to the literals scattered through cli.py / extraction/extractor.py before
# this module existed, so unset-env behavior is unchanged.
REGISTRY_PATH = os.environ.get("GPU_AGENT_REGISTRY", "registry/indicators.json")
TAXONOMY_PATH = os.environ.get("GPU_AGENT_TAXONOMY", "docs/taxonomy.json")

# F63: corroboration threshold N — distinct publishers (F31 identity) required to unlock
# one bounded step (gate F2e high-confidence lift, thesis rule 6 corroborated reversal,
# evidence-sufficiency gate). Single tunable; the amended SYSTEM prompts hardcode the same
# number and tests/test_corroboration_config.py guards the coupling.
CORROBORATION_PATH = os.environ.get("GPU_AGENT_CORROBORATION", "registry/corroboration.json")


@lru_cache(maxsize=1)
def min_distinct_publishers() -> int:
    import json
    import pathlib
    try:
        return int(json.loads(pathlib.Path(CORROBORATION_PATH).read_text("utf-8"))
                   ["minDistinctPublishers"])
    except FileNotFoundError:
        return 3
