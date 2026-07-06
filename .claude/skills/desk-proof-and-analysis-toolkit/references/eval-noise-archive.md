# Eval noise archive — the identical-bundle data behind recipe 1 and recipe 2

Supplementary to `SKILL.md` recipe 1 (replicate & noise analysis) and recipe 2 (gate-power
analysis). This is the raw data the eval-v2 design used to derive ε and the data F73 cites
as evidence the gate's discriminative power is unproven. Re-verify against the cited files
before quoting any number as current — this is a snapshot of runs through 2026-07-05.

## Identical-bundle seam-mean swings (source: `docs/superpowers/specs/2026-07-05-eval-v2-replicate-baseline-design.md` §Problem)

| identical-bundle group | extract | judge | thesis |
| --- | --- | --- | --- |
| F62 a1/a2 (+a3 for extract & thesis — same hashes) | 6.25 / 6.75 / 6.75 | 6.50 / 6.25 (old judge prompt) | 6.00 / 6.00 / 6.00 |
| F63 r1/r2 | 6.375 / 6.375 | 7.00 / 6.75 | 6.00 / 5.50 |

Per-seam swing on identical prompts: extract 0.50, judge 0.25, thesis 0.50 — one to four
grading quanta (quanta: extract 0.125, judge 0.25, thesis 0.50, at the 2026-07-05 case
count). This table is what motivated the whole eval-v2 redesign: the old v1 bar was a
single draw sitting inside this noise band.

## The three post-eval-v2 replicate sets, in full (all re-verified 2026-07-06 against the files cited)

### Migration baseline (`docs/superpowers/eval-notes/2026-07-05-eval-v2-migration-run-notes.md`)

| replicate | provenance | extract | judge | thesis |
| --- | --- | --- | --- | --- |
| r1 | archived F62 attempt-3 | 6.75 | 7.50 | 6.00 |
| r2 | fresh full run, 2026-07-05 | 6.75 | 7.75 | 6.00 |
| r3 | fresh full run, 2026-07-05 | 6.625 | 7.50 | 6.50 |

seamMeans: extract 6.7083, judge 7.5833, thesis 6.1667. ε: extract 0.125 (quantum floor,
half-range 0.0625), judge 0.25 (quantum floor, half-range 0.125), thesis 0.5 (floor,
half-range 0.25). Bars (mean − ε): extract 6.5833, judge 7.3333, thesis 5.6667. This is
the bar the F63 re-gate below was judged against.

### F63 re-gate (`docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md`) — became the CURRENT committed baseline

| replicate | extract | judge | thesis | note |
| --- | --- | --- | --- | --- |
| r1 (gate run) | 6.625 | 7.75 | 6.00 | PASS vs the migration bars above — margin on extract: 6.625 − 6.5833 = **0.0417** |
| r2 (top-up) | 6.50 | 7.50 | 6.00 | printed MARGINAL-FAIL vs the migration incumbent — informational only for an unfiltered top-up, kept regardless |
| r3 (top-up) | 7.125 | 7.50 | 6.00 | incidentally passed the migration bar on its own |

New baseline from r1+r2+r3: seamMeans extract 6.75 / judge 7.5833 / thesis 6.0; ε extract
0.3125 (half-range (7.125−6.5)/2), judge 0.25 (quantum floor), thesis 0.5 (floor). Bars
(mean − ε): extract 6.4375, judge 7.3333, thesis 5.50. Dispersion guard: max seam range
0.625 (extract) ≤ 1.0 — clean. **This is the baseline committed in `fixtures/evals/baseline.json`
today** — re-verify with `git show HEAD:fixtures/evals/baseline.json` or a direct read.

## A 2026-07-06 finding from re-running recipe 1's script against this exact triple

Running `scripts/measure_seam_noise.py` against the three retained
`eval-f63-regate-2026-07-05/{r1,r2,r3}/report.json` files (this session) reproduces the
committed baseline's seamMeans/epsilon exactly (see `SKILL.md` recipe 1), AND surfaces a
per-case swing of **3** on `extract-2026-07-05` (totals 6, 4, 7 across r1/r2/r3) — larger
than the eval-v2 design spec's own "historical false-positive check" claim that "max
per-case swing between identical-prompt runs in the archive is 2" (that check predates
this triple; it was run against the F62/F63 archive, not against the runs that became the
current baseline). This does not mean the gate is broken — `extract-2026-07-05`'s crater
line is `median(6) − 3 = 3`, so a swing down to 4 does not crater — but it is live,
dated evidence that the "max swing = 2" claim needs re-running against the fuller archive
before anyone cites it as still true. Re-run the script yourself before trusting either
number; this is exactly the kind of claim recipe 1 exists to keep honest instead of quoted
from a doc.

## extract-2026-07-05 (formerly "extract-05"): the chronically weak case

Flagged in multiple run notes as "the weakest case across every run ever recorded" (4–7
band, completeness the recurring 0 criterion). Its baseline median is 6 with the crater
line at 3. Nobody has diagnosed whether the underlying case (the source document) or the
extraction prompt is at fault — logged as an open observation in
`docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md`, not a bug in the eval
harness. If you're using this case in a canary design (recipe 2), be aware it already runs
hotter/noisier than the other 7 extract-positive cases — a canary should probably avoid
leaning on this specific case to demonstrate gate power, since its baseline noise is
already the highest in the set.
