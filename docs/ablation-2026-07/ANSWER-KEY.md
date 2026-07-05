# ANSWER KEY — blind ablation 2026-07 (do not open before scoring SCORING.md)

- **A** = rss-digest: RSS-digest baseline: one fresh web-only subagent, zero repo context, prompt = 'Summarize the last ~45 days of merchant GPU market news (NVIDIA, AMD; demand, supply, pricing, HBM, export controls) as a one-page digest for an executive. Cite a source per item.'
- **B** = desk: the desk (GPU Category Agent): July 2026 monthly flagship render + 2026-07-05 daily render, verbatim from the committed store (scorecards 2026-07-v3 and 2026-07-05-v1)
- **C** = deep-research: one-shot deep-research baseline: one fresh web-only subagent, zero repo context, prompt = 'Assess the current state of the merchant GPU market for a TSMC executive: demand vs supply, the binding constraint, key risks, what to watch next. 1-2 pages, every claim cited.'

Notes:
- Assignment was random (Python random.shuffle at build time).
- Normalization applied: one added title line per file ('# Artifact X — ...'); the
  deep-research agent's leading process narration (verifier chatter before its own
  document title) was trimmed; content otherwise untouched. Blinding is imperfect —
  the three house styles are visibly different (noted in SCORING.md).
- Contamination check: the two baseline agents ran web-only with zero repo context;
  their citations were verified to be web sources only (no repo/store paths).
- The desk artifact is a pure projection of the committed store and replays for $0.
