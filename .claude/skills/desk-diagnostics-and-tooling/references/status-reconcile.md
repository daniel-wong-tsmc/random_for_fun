# status_reconcile.py -- design notes and verified false positives

This file documents how `status_reconcile.py` decides "merged" vs "open," and the false
positives that shaped that design -- read this before extending the heuristic or trusting a
`CHECKBOX_AHEAD`/`STALE_CHECKBOX` verdict on an item this file doesn't already cover.

## The three tiers of "strong" merge evidence

1. **Backlog-cited hash.** A hex token in the item's own backlog paragraph that appears
   immediately AFTER the word "merge(d)" (not merely nearby) -- e.g. "DONE (merged to main
   `257cf1b`)", "DONE (merged 7197226)", "DONE (merged `e167c6b`, suite 923/3)". Directional on
   purpose.
2. **A real merge commit.** `git log --all --grep=F<n>\b --merges` -- an actual
   `Merge branch '...'` commit whose message mentions the item.
3. **Subject-line, non-`docs(...)` commit.** The F-number appears in the commit's SUBJECT line
   (not just its body) and the type prefix isn't `docs(`.

A commit that merely *discusses* an item in its body (e.g. "the F71 deadlock did not recur
this cycle" inside a `store(...)`/`fix(F74)` commit describing something else) is real,
findable history but is NOT evidence of a fix for that OTHER item -- because `merge-base
--is-ancestor` is trivially true for anything already on mainline, treating plain body
mentions as "merged" produces false `MERGED` verdicts for genuinely open items.

## False positives found and fixed while building this script (2026-07-06)

| Item | What went wrong | Root cause | Fix |
|---|---|---|---|
| F71, F73, F75 | Read as `MERGED` | Their only git hits were `docs(handoff)`/`docs(backlog)` commits mentioning them in passing (e.g. "the F71 deadlock did NOT recur"); a naive "any grep hit that's an ancestor = merged" rule can't tell that apart from a real fix | Restricted "strong" evidence to the three tiers above; these three now correctly report `OPEN_WITH_ACTIVITY` |
| F76 | Read as `STALE_CHECKBOX` (merged via `da58b94`) | F76's own backlog prose quotes `da58b94` as an EXAMPLE of the bug it's about ("title `da58b94` says F63 merged") -- the hash precedes the word "merged" in that sentence, not follows it | Made the hash-extraction regex directional: only capture a hash that comes AFTER "merge(d)", never a hash merely near the word in either direction |
| F2, F28 | Read as `CHECKBOX_AHEAD` ("no commit anywhere mentions F2") | Genuinely no commit in history tags these by F-number at all -- they were part of an early Wave-0 batch fix before the "cite the F-number" convention existed | Not fixable from git alone; both are real `[x]` items that happened to predate individual tagging. Treat "no commit mentions F&lt;N&gt;" + item number ≤ ~F51 as "needs a human glance," not evidence of a problem |
| F39 | Read as `CHECKBOX_AHEAD` | Its actual follow-up fix commit is `a2f6906 docs(F39 review fix): ...` -- a real content change (report wording) that happens to use a `docs(` prefix, which the subject-line tier deliberately excludes to avoid the F76/da58b94 class of false positive | Accepted as a known false positive of the `docs(` exclusion; the tradeoff (excluding real `docs(F..)` fixes to avoid counting `docs(backlog)` announcements) was chosen deliberately -- see next section |
| F9 (and other pre-lane-era items) | Would have been `CHECKBOX_AHEAD` under an earlier draft that only trusted tiers 1-2 | F9's fix (`c1b90f0 feat(v1.2): anchor polarity track defined ... (F9)`) has no "merged &lt;hash&gt;" phrase and is not a dedicated merge commit -- it's a direct Wave-1 commit | Added tier 3 (subject-line, non-docs) specifically to catch this shape |

## Why `docs(` commits are excluded from tier 3, even though it costs F39

The alternative -- trusting ANY commit with F&lt;N&gt; in its subject line, `docs(` or not --
was tried first and produces exactly the F76/`da58b94` failure mode one level up: `docs(backlog):
F71 - anchor-bound vs evidence-sufficiency gate deadlock, bypass too blunt` has "F71" in ITS
OWN subject line too (it's the item's opening/creation commit). Trusting subject-line hits
regardless of prefix would flag every backlog item as "merged" the moment it's opened. Excluding
`docs(` is the simpler, safer rule; it undercounts a handful of `docs(F.. review fix)` commits
(F39) at the benefit of not overcounting the much larger, much more consequential class of
"this commit just announces the item" commits.

## What this script cannot see: closure-by-prose

F61's backlog paragraph is still open text, its checkbox is `[ ]`, and there is no F61-tagged
commit anywhere -- yet `docs/superpowers/HANDOFF.md` says outright: "F61 is DONE (subsumed by
F67)." That is a real closure, recorded only as prose, with no commit of its own to point at
(F67's commits don't mention F61 either). `status_reconcile.py` surfaces the HANDOFF line as an
informational hint precisely because it can't verify this kind of claim from git alone --
treat any `HANDOFF.md says:` line printed alongside an `OPEN`/`OPEN_WITH_ACTIVITY` verdict as a
prompt to go read that line yourself, not as something the tool has already resolved.

## Re-verifying this file

The specific commits and verdicts named above are as of main @ `f7c83f0` (2026-07-06). Re-run
`status_reconcile.py --all` to see the current set; if new false positives appear, add them to
the table above rather than silently tweaking the heuristic (the tradeoffs here were each
chosen against a concrete counter-example, not in the abstract).
