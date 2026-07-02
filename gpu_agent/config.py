from __future__ import annotations
import os

# F42: hardcoded registry/taxonomy paths, centralized and env-overridable. Defaults are
# byte-identical to the literals scattered through cli.py / extraction/extractor.py before
# this module existed, so unset-env behavior is unchanged.
REGISTRY_PATH = os.environ.get("GPU_AGENT_REGISTRY", "registry/indicators.json")
TAXONOMY_PATH = os.environ.get("GPU_AGENT_TAXONOMY", "docs/taxonomy.json")
