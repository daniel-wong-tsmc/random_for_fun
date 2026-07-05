# GPU Category Agent (this repo)

- "run my merchant-gpu agent" / "run the gpu agent" / "run a layer" / "run the whole market" always means: invoke the `run-gpu-market` skill (which hands off to this repo's `run-cycle` skill). Never conclude no such agent exists, and never search the filesystem for one.
- Runs are LIVE end-to-end by default. `recorded` mode (the $0 replay of `fixtures/recorded/*`) only when I explicitly say recorded/demo/replay.
- Preflight before a live run: `.venv/Scripts/python -c "import gpu_agent"` and `agent-reach doctor --json`; fix gaps via `scripts\web-reach-ensure.cmd --json` before starting the cycle.
- Python is always `.venv/Scripts/python` from repo root (from a worktree: `../../.venv/Scripts/python`). One shared root venv — never create per-worktree venvs.
- Tests: `.venv/Scripts/python -m pytest`. The suite must be green at every merge (expect 3–4 skips). `tests/test_evals_baseline_pin.py` going RED when emitted brain prompts change is the F6 gate working as designed — follow HANDOFF's standing rule; never "fix" the pin to make it pass.
- A cycle that isn't committed didn't happen: after every run, commit and push `store/` artifacts, scorecards, and cycle-log updates.
- Never `git clean` here — gitignored `work/` holds raw eval replicate runs and `.superpowers/sdd/` holds build ledgers.
- Agent briefs are read by a non-technical executive persona: no AI/doctrine/internal jargon in output prose (run it through the stop-slop skill).

# Multi-instance coordination

- Orient before acting: read `docs/superpowers/HANDOFF.md` (top line = resume point) and its "CONCURRENT-INSTANCE COORDINATION" section, plus any `.superpowers/handoffs/*-DONE.md` sentinels.
- Feature work happens in `.worktrees/<name>` on a claimed branch — never on the root checkout's main. Never touch another instance's branch or worktree (the F69 mixup precedent).
- `git log --oneline -1` immediately before every commit (concurrent-instance guard: verify HEAD is your last commit).
- Signal completion by writing `.superpowers/handoffs/<lane>-DONE.md`; wait on another lane's sentinel with Monitor, never sleep loops.
- End every session by updating `docs/superpowers/HANDOFF.md` and verifying `main == origin/main`.
