# store_inspect.py -- field-by-field reference

Verified against the live store on main @ `f7c83f0` (2026-07-06). Counts below are
date-stamped; re-run the commands in the table at the end of the main SKILL.md to get today's
numbers -- they are cited here as worked examples, not as facts to quote going forward.

## `latest` -- the mixed-grain trap, precisely

Scorecard filenames are `<asOf>-v<N>.json` where `asOf` is either month grain (`2026-07`) or
day grain (`2026-07-05`), matching `gpu_agent/report.py::_VERSION_RE`. The code that picks
"the prior scorecard" (`report.find_prior`, `memory.latest_scorecard_before`) sorts candidates
by `(asOf_string, version)` **lexically descending** -- it does not parse `asOf` as a date.

Because `"2026-07"` is a string-prefix of `"2026-07-05"`, and Python ranks a string that is a
strict prefix of another as *smaller*, `"2026-07-05" > "2026-07"` in plain string comparison.
Sorted descending, `"2026-07-05"` sorts ahead of `"2026-07"`. Concretely, in
`store/chips.merchant-gpu/` today: `2026-07-05-v1.json` (a single day's daily run) sorts as
"more recent" than `2026-07-v3.json` (the monthly flagship, produced from a full month of
gathering and judged as of the same week) under the CODE ORDER the real code uses. This isn't
a bug filed anywhere as such -- `report.py`'s own docstring says grain consistency is "enforced
wiki-side by another stream, not here" -- but any tool or script that auto-detects "the latest
scorecard" with no explicit filename will silently pick the day-grain file, not the one a human
would call "the current state of the desk."

`store_inspect.py latest` prints both orderings side by side and says explicitly when they
disagree, so you always know which file a `find_prior(current_path=None)` caller would
actually pick before you make a decision that assumes otherwise.

## `findings` -- what the by-side/by-kind counts mean

`kind` is one of `observed | measured | hypothesis` (the Finding schema's own vocabulary,
Part 7). `side` is `demand | supply | price | structural`. Both come straight off the stored
JSON; there is nothing to compute. The two id-generation buckets:

- **pre-F52**: `<host-slug>-<hash8>-<n>` -- no vintage segment. A URL re-gathered on a later
  day could, before F52, mint a colliding finding id with an existing one from an earlier day.
- **post-F52**: `<host-slug>-<hash8>-<asOf>-<n>` -- vintage-scoped, so a re-gathered URL on a
  later `asOf` always mints a fresh id.

Both generations legitimately coexist in `store/findings/` today (this store predates F52).
Don't read the pre-F52 shape as corruption.

There is deliberately no "gate outcome" breakdown here: `store/findings/` is populated only
after `gate.check_finding` accepts a draft, so every file in it already passed. If you want
pass/reject counts, that's an EVAL-ONLY concept (`fixtures/evals/cases/*.json`'s
`checks.gateOutcome`) -- see `eval_diagnostics.py case-census` and
references/eval-diagnostics.md, and don't conflate the two "gate" ideas; they measure
different things over different data.

## `dedup` -- L1 vs L2, and how to read `docsDroppedKnown`

Two independent dedup layers exist in this codebase:

- **L1 (document-level)**: `store/seen_docs.jsonl`, one JSON object per line:
  `{"url", "hash", "asOf"}`. Keyed by content HASH first (a stable URL whose content changed
  is treated as a NEW document -- F12's deliberate design, so a price page that updates daily
  is never permanently invisible just because its URL repeats). Only used when a run threads
  `--dedup-store` through `ingest` (i.e., daily-mode runs); standard live-mode runs do no L1
  filtering at all.
- **L2 (finding-level)**: `store/<category>/dedup-<asOf>.json`, produced by `wiki-dedup`.
  Normal key: `(entity, indicatorId)`. Price-side findings get a 4-tuple per F51:
  `(entity, indicatorId, publisher-netloc, unit)` -- because two providers (or two SKUs at the
  same provider, still an open gap per `dedup.py:205-207`) quoting the same indicator would
  otherwise collide into one series and fabricate a price swing that's actually just "two
  different vendors, same day."

`store_inspect.py dedup` reads only L2 (the report file). Its `docsDroppedKnown` count is
whatever L1 recorded for that run *if* L1 ran at all -- a `0` there does not mean "no
duplicates," it can mean "L1 wasn't threaded through this run" (check the run's mode/flags,
not this field alone, before concluding anything about document-level duplication).

## `wiki-lint` -- why this reads log.jsonl instead of calling the CLI

`gpu_agent.wiki.lint.lint()` defaults to `record=True`: the first time it's called for a given
`as_of` it appends a `"kind":"lint"` event to `store/wiki/log.jsonl` -- a genuine WRITE to the
tracked store. It only becomes a no-op on a SECOND call for an `as_of` that's already been
linted (verified directly: running the real `gpu-agent wiki-lint --as-of <today's already-run
date>` produced no git diff; a fresh `--as-of` would have). Because this script must stay
read-only regardless of what `as_of` you're curious about, it reads the log directly and reports
the most recent lint event rather than ever invoking the CLI form.

Field meanings (from `lint.py`'s own scoring):

- **material** -- pages whose latest observation(s) crossed the materiality threshold this
  cycle (the render-worthy moves).
- **dropped** -- candidate moves that scored below that threshold (F34's fold; not an error,
  just filtered).
- **stale** -- pages whose half-life decay has run past config with no fresh observation.
  Candidates for a future lifecycle prune pass; nothing currently removes them (open,
  F25-adjacent).
- **orphans** -- observations or cross-refs pointing at findings/pages lint couldn't resolve.
  Data-quality signal, not fatal, and not blocking anything today.
- **contradictions** -- a fresh observation conflicting with a page's own recorded trajectory.
  Surfaced in the log, never silently resolved.

These counts accumulate with no landed cleanup mechanism (open problem). A nonzero
stale/orphans count on any single lint snapshot is expected background noise; what would
actually be worth escalating is the *trend* climbing lint-over-lint with no corresponding
lifecycle action, which this script doesn't compute for you (it prints only the latest event) --
diff two lint events by `seq` if you want that.

## `thesis` -- what divergence means, and why this doesn't reimplement the fold

`store/theses/<category>/book.json` is a materialized view; `history.jsonl` is the append-only,
canonical source. `ThesisStore.write()` always appends to history FIRST, then rewrites
`book.json` -- so a crash between the two leaves history ahead of the book, never behind.
`ThesisStore.load()` (the function every real caller goes through) replays `history.jsonl` from
scratch and refuses to return `book.json` at all if it disagrees with that replay.

An early draft of this diagnostic reimplemented that fold in pure stdlib (parse each
`history.jsonl` line, merge by thesis id, last-write-wins) to avoid a pydantic/gpu_agent import.
It produced a **false DIVERGENCE alarm** on a perfectly healthy 13-entry book, because
`ThesisEntry` carries several derived fields (`streak`, `pendingChallenge`, `lastDirection`,
provenance metadata) that a naive last-write-wins dict merge does not reproduce byte-for-byte --
the reimplementation was incomplete, not the store. Shipping a diagnostic that cries wolf on
healthy data is worse than not shipping one, so `store_inspect.py thesis` instead subprocesses
the repo's own `.venv` python to call the REAL `ThesisStore(...).load()` and reports exactly
what it says. This is still read-only (`load()` only reads two files) and it is the actual
logic every other caller trusts, not a lookalike of it.

If you ever see a genuine divergence reported: it means something wrote `book.json` directly,
bypassing `ThesisStore.write()`. Never hand-edit `book.json` back into shape as the fix --
find and stop whatever produced the direct write, and let a subsequent real `write()` call (or
a deliberate rebuild-and-rewrite) reconcile it.
