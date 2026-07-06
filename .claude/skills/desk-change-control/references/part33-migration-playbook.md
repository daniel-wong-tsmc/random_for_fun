# Part-33 Migration Playbook — the two worked precedents, in full

Companion to `desk-change-control` SKILL.md §3. Read this before writing migration #3.
Verified against main @ 639c00d, 2026-07-05. Primary sources: `docs/migrations/2026-07-contract-v1.2.md`,
`docs/migrations/2026-07-contract-v1.3.md`, charter Part 33 (`docs/agent-swarm-charter.md`, ~lines 1417–1438),
commits 54b45d6, 859ac35, bb67455, 34aed10, bfd6571.

Charter Part 33's rule, verbatim: "the contract is frozen *within* a version and evolves *across*
versions, with old data always readable." Additive by default; a breaking change bumps the major
version and ships an up-migration view, not an in-place rewrite; deprecated fields stay written
(marked) ≥ N cycles before removal.

## Precedent 1 — Contract v1.2 (2026-07-02): the maximal form

**What it was.** The Wave-1 bundle of the 2026-07-02 full-repo review: 14 rule changes shipped as
ONE coupled migration because they all touch the frozen contract. Lanes A (gate/extraction/schema)
and B (scoring/briefing/pipeline/registry) ran as a single worktree `fix/contract-v1.2` for exactly
this reason — "Contract v1.2 approved as ONE migration" (decision recorded in commit 54b45d6 and
`docs/fix-backlog.md:495-501`).

**The doc** (`docs/migrations/2026-07-contract-v1.2.md`) contains, in order:

1. Header: date + "user-approved 2026-07-02" + one-paragraph scope.
2. **Rule changes, one line each, keyed by F-id** (F2a–e, F3, F7, F8, F9, F16, F17, F21, F36, F37).
3. A named section for the biggest behavioral delta (**"The D6 flip"** — scoring indicator to
   price overlay, weight 0.12 → 0.0), so future readers can attribute index deltas.
4. **schemaVersion decision**: newly extracted findings stamp `"1.2"` (was 1.1); stored 2026-06
   findings REMAIN 1.1 historical records.
5. **Honesty section**: "Would the stored 2026-06 findings pass the v1.2 gate? No — that is the
   point of the migration" — quantifies exactly what the old gate had admitted (20 future-dated,
   20 registry-contradicting findings in 2026-06-v6).
6. **Shadow-run table**: `scripts/shadow_run_v12.py` recomputes DMI/SMI/anchors two ways over the
   SAME stored findings — old = a frozen inline copy of the pre-v1.2 algorithm, new = the current
   package. **No store writes.** The doc's table shows old/new DMI/SMI per stored version with
   delta notes attributing every difference to a named rule (D6 drops, entity un-shadowing).
7. **Replay mapping**: `scripts/replay_v12.py` recomputes each stored scorecard under v1.2 math and
   APPENDS it as a new immutable version (2026-06 v1..v6 → v7..v12) with `provenance.replayOf` +
   `provenance.migration=contract-v1.2`. Findings/ratings/narrative copied verbatim — **the replay
   re-runs the MATH, not the gate**. Originals byte-unchanged. v12 becomes the latest-version math
   so `find_prior` comparisons stay continuous.

**Golden fixtures.** Regenerated ONCE under v1.2 math (commit 859ac35), with an **independent hand
computation in the commit message** — every DMI/SMI contribution term written out
(`dmi += .10*1*2/3 = .066667` etc.) and the closing line "Regenerated file matches exactly."
This is the bar: a regenerated golden is only evidence if a human-readable computation that did
NOT run through the code arrives at the same numbers. (`fixtures/golden/` pins the deterministic
scoring path via `tests/test_golden_integration.py`; it is regenerated ONLY inside a migration.)

**Review pattern (observed).** Opus-class review on the contract diff; the migration merged only
with the full suite green (516/3 at Wave-1 integration f1c0835).

**Known trap recorded at Wave 2:** F41's `Finding.schemaVersion` default bump was **explicitly
skipped** ("F41 minus the frozen schemaVersion-default bump", `docs/fix-backlog.md:17`) even though
F41's own entry still lists it — the wave note wins. The schema default remains un-bumped by
deliberate decision; do not "fix" it in passing.

## Precedent 2 — Contract v1.3 (2026-07-04): the minimal form

**What it was.** F63's corroboration lift: gate F2e gains exactly one exception — all-secondary
evidence CAN carry `confidence=high` if it spans ≥ N distinct publishers (N=3 in
`registry/corroboration.json`; publisher identity = F31's `publisher_key`, so same-domain
syndication counts once). Shipped as `feat(gate)!:` (breaking-change marker, commit bfd6571).

**The doc** (`docs/migrations/2026-07-contract-v1.3.md`) shows the minimal shape still carries
every section:

1. Header: "The second sanctioned frozen-core migration… user-approved 2026-07-04 in the F63
   design" (approval lives in the spec, cited by path).
2. The ONE rule change, with the new error text quoted (`(K distinct publishers < N)`).
3. **"Deliberately unchanged"** — names what a reader might assume moved but didn't: F3's
   dimension-level confidence-cap badge, and "everything else in the frozen set is byte-identical
   to v1.2", including **schemaVersion stays 1.2 — no schema field changed**.
4. **"Companion doctrine (same branch, not frozen-core)"** — separates the migration proper from
   the non-frozen work that rode the same branch (thesis rule 6, `gpu_agent/sufficiency.py`,
   charter Part 37 amendment). Keep this separation: only the frozen-core delta is the migration.

**No shadow-run/replay tables in v1.3.** A gate-rule change with no scoring-math delta has nothing
to shadow or replay — but the doc says so explicitly rather than silently omitting the sections.
If your change touches scoring math or stored-series continuity in ANY way, the v1.2 machinery is
mandatory.

**v1.3 also shows the eval coupling:** F63's prompt amendments (corroboration scope wording etc.)
tripped the pin and went through two eval FAILs, the eval-v2 rebuild, and a re-gate PASS
(ef52790) before the branch merged (017b592). A migration whose companion work touches prompts
inherits the full §4 eval governance on top of this playbook.

## The template for migration #3

- [ ] User approval, recorded and citable (spec section or migration-doc header). Never AFK-defaulted.
- [ ] One coupled migration branch/worktree; nothing frozen ships piecemeal.
- [ ] `docs/migrations/2026-MM-contract-v1.N.md` with: header + approval; rule changes one line per
      F-id; biggest-delta section if math moved; explicit schemaVersion decision either way;
      "Deliberately unchanged"; "Companion doctrine" if non-frozen work rides along.
- [ ] Shadow-run (no store writes) + diff table, if any computed value can differ.
- [ ] Replay appending new store versions with `provenance.replayOf`, if stored series continuity
      is affected. Replay = math only, never re-gating history; originals byte-unchanged.
- [ ] Golden fixtures regenerated once + independent hand computation in the commit message.
- [ ] Full suite green; pin re-checked; eval flow if prompts moved.
- [ ] Opus-class review on the frozen diff; branch to "awaiting user merge go"; user merges.
- [ ] Charter reconciled: if the migration lands doctrine the charter defers ("Not yet…"), amend
      the deferred list too — the Part 37 line-~1637 contradiction exists because F63 didn't.

## Candidates already queued for this path (2026-07-05)

- **F71** gate precedence (anchor bound vs sufficiency): "Gate-semantics change → ships as a
  Part 33 versioned migration" (`docs/fix-backlog.md:463-484`).
- **F72** publisher-distinctness counting in F2e: "the F2e counting change still needs a Part-33
  migration" — pairs with F71.
- **F60**'s scoring-side half: registry weights are DATA (safe), but any `scoring.py` side-semantics
  change is frozen-core.

Route execution of the F71/F72 cluster through `gate-integrity-campaign`.
