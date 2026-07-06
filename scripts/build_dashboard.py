"""CLI: build the merchant-GPU showcase dashboard (deterministic, LLM-free)."""
import os
import sys

# Ensure the local package (this checkout / worktree) is imported, not an
# editable-installed copy at another path. scripts/ is one level below the root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gpu_agent.dashboard.build import main

if __name__ == "__main__":
    sys.exit(main())
