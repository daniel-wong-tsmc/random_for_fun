# F72 adversarial test — real store precedent + a constructed fixture

Backing detail for Phase 3 of `SKILL.md`. `gpu_agent/publisher.py::publisher_key` keys
corroboration by URL netloc only (www-stripped, lowercased) — see `market-state-reference` §6 for
the doctrine; this file is the concrete "does a real exploit instance already exist in the
store" check plus a fixture sketch for the pinned test the fix will need.

## 1. What actually exists in `store/` today (checked 2026-07-06)

```
Select-String -Path store/chips.merchant-gpu/*.json -Pattern 'stocktitan\.net|financialcontent\.com|finance\.yahoo\.com'
```

The three "archetypal PR-syndication endpoints" the backlog names (`docs/fix-backlog.md:572-573`)
DO appear in the live store, individually:

| Domain | Where seen | Nature |
|---|---|---|
| `stocktitan.net` | `store/chips.merchant-gpu/2026-06-v2.json`, `-v10.json`, `2026-07-v2.json`, `2026-07-v3.json`, plus standalone `store/findings/www-stocktitan-net-*.json` | SEC-filing mirror pages (8-K/10-Q re-hosts) |
| `finance.yahoo.com` | `store/chips.merchant-gpu/2026-07-v3.json`, `store/findings/finance-yahoo-com-*.json` | Wire-story syndication |

**No single scorecard in the store today has all three domains co-cited as the distinct-publisher
set for ONE dimension's rating change or bottleneck shift.** The closest co-occurrence is
`2026-07-v3.json`, which has both `stocktitan.net` (3 hits) and `finance.yahoo.com` (2 hits) but
not `markets.financialcontent.com`, and there is no evidence (re-check before citing further)
that those citations were the same underlying wire story rather than genuinely distinct
reporting. **Conclusion: F72 is a proven STRUCTURAL risk (the endpoints the exploit would use are
already flowing through the live gatherer), not yet a WITNESSED silent failure** — the adversarial
test needs a constructed fixture, not a replay of a real incident. Re-run the `Select-String`
above before citing this as still true; the store grows every cycle.

## 2. Constructed fixture sketch (proposed — not yet a real pytest file)

Model on `tests/test_gate_registry_integration.py` / `tests/test_corroboration_config.py`'s
fixture style. Three `Finding`s, same claim, evidence URLs on three syndicator netlocs, bodies
near-identical (simulating one wire release):

```python
def _wire_syndicated_findings():
    body = ("Acme Corp announces expanded GPU capacity agreement with hyperscale "
             "customer, effective Q3.")  # identical/near-identical across all three
    urls = [
        "https://www.stocktitan.net/news/ACME/acme-corp-announces-abc123.html",
        "https://markets.financialcontent.com/stocks/news/read/ACME/acme-corp-announces",
        "https://finance.yahoo.com/news/acme-corp-announces-capacity-deal.html",
    ]
    return [
        _finding(fid=f"wire-{i}", excerpt=body, url=u, tier="secondary")
        for i, u in enumerate(urls)
    ]
```

Expected behavior TODAY (pre-fix): `publisher_key` returns 3 distinct netlocs → `check_sufficiency`
/ gate F2e / thesis rule 6 / wiki promotion all see `distinct publishers = 3` and treat the claim
as fully corroborated — **this passes silently, which is the bug**. A test asserting today's
(wrong) behavior documents the hole; a second assertion (skipped/xfail until the fix lands) states
the target behavior:

- Target: content-similarity collapse (F72 fix option a) or a `registry/syndicators.json`
  originating-publisher list (option b) must reduce the above to **1** distinct publisher, so
  `check_sufficiency`/gate F2e correctly reports `< 3` and refuses the corroborated-claim path.
- A companion assertion with 3 genuinely distinct outlets (different claims, different bodies,
  none on a known syndicator netloc) must still pass at `distinct publishers = 3` — the fix must
  not make corroboration impossible, only make syndication uncountable.

## 3. Consumers that inherit the fix "for free" via the shared key

`publisher_key` is imported independently in three places — fixing it once (not three times) is
the point of using the shared function (do not let a lane re-derive distinctness locally):

- `gpu_agent/gate.py:6,35` — gate F2e's corroboration count.
- `gpu_agent/wiki/lifecycle.py:59,71` — wiki page promotion's publisher count.
- `gpu_agent/thesis.py:477` (imported as `_evidence_publisher`) — rule 6's corroborated-reversal
  exception.

A pinned test for each of these three call sites (or one shared fixture reused across three test
files) is the acceptance bar `SKILL.md` Phase 3 references — "thesis rule 6 and wiki promotion
inherit via the shared key" is a claim to verify, not assume, once the fix lands.
