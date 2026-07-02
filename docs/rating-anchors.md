# Rating Anchor Definitions (F39)

## Purpose

A dimension rating names a **market position** on that dimension — Very strong, Strong, Mixed,
Weak, or Very weak — not a mood, and not a restatement of how confident the writer feels about the
evidence. Per the charter's Part 17 (`docs/agent-swarm-charter.md`), the rating is one of three
parts of a judgment (rating + direction + confidence), and it exists precisely so that two analysts
looking at the same evidence pick the same word.

Two things bound the choice:

1. **The numeric anchor bounds it.** Every rating cites the Finding(s) and any measured metric
   behind it — a growth rate, a margin, a lead time, a concentration figure. The rating can never
   contradict the direction of its cited measured anchor: a "Very strong" rating against a deeply
   negative print is rejected (Part 17's bias guardrail). Code checks that bound; it does not choose
   the word.
2. **The words in this doc decide within that band.** Given evidence that clears the bound, which
   of the five words applies is decided by the discriminators below — a stated, checkable observable
   that separates each rating from its neighbor, never an adverb ("very," "somewhat," "pretty")
   standing in for a missing distinction.

This doc defines the **rating word only**. It does not define direction (improving / steady /
worsening) or confidence (low / medium / high) — those are separate fields on the same judgment. A
dimension can legitimately be rated "Weak, improving, medium confidence": a weak position today that
is getting better. Don't smuggle trend into the rating word; that is what the direction field is for.

**The bottleneck/strategicRisk inversion.** For four of the six dimensions — momentum,
unitEconomics, competitiveStructure, moat — "Very strong" means the category is in a strong
position. For the other two, **bottleneck** and **strategicRisk**, "Very strong" means the opposite
kind of thing: it rates the presence of the factor itself, not the category's position. A "Very
strong" bottleneck rating means this is a very strong choke point (bad news for whoever is stuck
behind it); a "Very strong" strategicRisk rating means very high risk exposure. It is not a
compliment. See those two sections below for the discriminators, stated explicitly.

---

## Momentum (`momentum`)

Growth rate of the category's core quantity — revenue, capacity, gigawatts, share — right now,
independent of where it is heading next (that is the separate direction field). The discriminator
across ratings is **who or what is setting the pace**: demand outrunning the category's own capacity
to serve it, versus the category simply growing, versus flattening, versus shrinking.

| Rating | Definition | Falsifiable marker |
|---|---|---|
| Very strong | Growth in the core quantity is outrunning the category's own capacity to keep up — the binding limit on growth is the capacity to serve, never the demand. | You should be able to point at a backlog, order book, or lead time that has extended to a new high alongside the growth. |
| Strong | The core quantity is growing faster than the category's own multi-year trend. | You should be able to point at a period-over-period growth figure that beats the trailing average, corroborated by more than one source. |
| Mixed | Growth continues, but the rate itself has decelerated, or growth diverges across sub-segments or geographies. | You should be able to point at a slower period-over-period growth figure than the prior period, or findings that disagree on whether growth continued. |
| Weak | The core quantity is flat — growth is at or near zero. | You should be able to point at a reported period-over-period change that rounds to roughly zero. |
| Very weak | The core quantity is shrinking. | You should be able to point at a reported period-over-period decline in the core quantity itself. |

---

## Unit economics (`unitEconomics`)

Margin or cost-per-unit trajectory — the direction and level of $/unit, $/output, or
retention-style economics. The discriminator is **whether the trajectory is improving, and how it
compares to the next-best alternative available to a buyer.**

| Rating | Definition | Falsifiable marker |
|---|---|---|
| Very strong | Cost-per-unit or margin is improving and is at or ahead of the best available alternative on the same metric. | You should be able to point at a reported cost or margin figure that beats the next-best cited alternative on the same metric. |
| Strong | Cost-per-unit or margin is improving, but has not been shown to lead the field. | You should be able to point at consecutive periods of margin expansion or cost decline in the same reported metric. |
| Mixed | Cost and margin move in offsetting directions, or improve in some segments while eroding in others. | You should be able to point at a finding where a cost or price decline is offset by a comparable decline elsewhere, netting to little change in margin. |
| Weak | Cost-per-unit or margin is flat, within the noise of the prior period. | You should be able to point at a reported figure that is statistically indistinguishable from the prior period. |
| Very weak | Margin is compressing, or cost is rising enough to threaten viability. | You should be able to point at a finding citing a named participant as unprofitable, writing down assets, or exiting on economics grounds. |

---

## Competitive structure (`competitiveStructure`)

Concentration and rationality of the competitive field — how many credible players there are, and
whether pricing discipline holds. The discriminator is **the count of credible players, and whether
that count is stable, narrowing, or widening.**

| Rating | Definition | Falsifiable marker |
|---|---|---|
| Very strong | The field is concentrated among a small number of credible players, and pricing discipline holds. | You should be able to point at a reported concentration figure — share of the top player, or a small named count of credible competitors — that has held or narrowed. |
| Strong | The field is moderately concentrated, and competition remains rational. | You should be able to point at a stable count of credible competitors across consecutive periods. |
| Mixed | The field is consolidating in one sub-segment while fragmenting in another, or entrants and exits roughly offset. | You should be able to point at findings showing new entrants in one sub-segment alongside consolidation in another. |
| Weak | The field is fragmenting — the count of credible competitors is rising, and pricing discipline is eroding. | You should be able to point at a reported increase in the count of credible competitors, or an explicit price war. |
| Very weak | The field is hypercompetitive or commoditized. | You should be able to point at a finding of a share leader losing share to multiple challengers at once, or a participant exiting on competitive grounds. |

---

## Moat & defensibility (`moat`)

Switching cost, ecosystem lock-in, and data/network effects — whatever keeps a customer from
leaving even when a cheaper or better alternative exists. The discriminator is **whether the
mechanism has been tested against a real alternative, and whether it held.**

| Rating | Definition | Falsifiable marker |
|---|---|---|
| Very strong | The mechanism has been tested against a credible, cheaper, or better alternative, and customers stayed anyway. | You should be able to point at a finding where a named customer or segment stayed despite a credible alternative being available. |
| Strong | A durable mechanism (proprietary data, network effect, ecosystem lock-in, high switching cost) is present and cited with evidence, but has not yet been tested against a real alternative. | You should be able to point at a specific structural mechanism cited with evidence, independent of any switching event. |
| Mixed | The mechanism is present but shows a first crack — a specific customer or segment switched, or a competitor closed the gap on that specific mechanism. | You should be able to point at a finding of one customer or segment switching, or one competitor closing the gap, without it yet being the broad pattern. |
| Weak | The mechanism is eroding broadly — switching or share loss is attributable to it in more than one finding. | You should be able to point at more than one finding of switching or share loss attributable to the same eroding mechanism. |
| Very weak | No mechanism holds customers in place; price is the primary purchase driver. | You should be able to point at a finding where price, not the mechanism, is cited as the deciding factor in a purchase or renewal. |

---

## Bottleneck / supply constraint (`bottleneck`)

Whether this category is the gating layer right now — lead times, queues, sold-out capacity.
**Inversion: "Very strong" rates the presence of the factor** — a very strong choke point — not the
category's position. A category can be rated "Very strong" here and be having a terrible time as a
result (buyers stuck behind it) or a great time (a seller with pricing power); that distinction is
what direction and narrative are for, not the rating word. The discriminator is **how binding the
constraint is, and on how much of the chain.**

| Rating | Definition | Falsifiable marker |
|---|---|---|
| Very strong | This is the binding constraint on the whole chain right now: demand provably outruns supply and the wait is the story. | You should be able to point at a lead time, queue, or backlog at or near a record, with buyers reported reserving capacity far in advance or paying up for it. |
| Strong | A real constraint exists and binds part of the chain, with more slack than the "Very strong" case. | You should be able to point at a lead time or queue elevated versus its own history but not at a record, or a constraint affecting some buyers but not all. |
| Mixed | The constraint is intermittent, or migrating from one node in the chain to another. | You should be able to point at a finding showing the bottleneck easing at one node while appearing at another, across periods. |
| Weak | A constraint is cited but is not binding — spare capacity exists alongside it. | You should be able to point at a finding of available or spare capacity reported alongside the cited constraint. |
| Very weak | No meaningful constraint — capacity is not gating anything. | You should be able to point at a lead time or queue at or below historical norms. |

---

## Strategic risk (`strategicRisk`)

Geopolitical, regulatory, capital-intensity, or circular-financing exposure. **Inversion: "Very
strong" rates the presence of the factor** — very high risk exposure — not the category's position;
it is not a compliment. The discriminator is **whether a concrete, dated trigger exists, or whether
the exposure is still theoretical.**

| Rating | Definition | Falsifiable marker |
|---|---|---|
| Very strong | Exposure is acute and immediate. | You should be able to point at a finding citing an enacted or imminent action — a sanction, export control, regulation, or financing structure under active scrutiny — with a named, dated trigger. |
| Strong | Exposure is material and plausible within the near term. | You should be able to point at a finding citing a proposed or pending action, or a named structural dependency (e.g., a specific circular-financing arrangement) that has been publicly flagged. |
| Mixed | Exposure exists but is diffuse or contested. | You should be able to point at findings that disagree — some flagging the risk, others citing a specific mitigating factor. |
| Weak | Exposure is low and mostly theoretical. | You should be able to point at a finding that names the risk category but cites no concrete trigger or pending action. |
| Very weak | Exposure is minimal or absent. | You should be able to point at a finding of explicit diversification — of suppliers, jurisdictions, or financing sources — that closes off the risk. |

---

## Examples

These illustrate the discriminators above using specific categories; the definitions themselves
stay category-agnostic and this is the only section where category-specific names appear.

- **Bottleneck, Very strong** — advanced chip packaging (CoWoS): capacity scaling from ~35k to ~130k
  wafers/month by end-2026, sold out, with GPU vendors having booked most of the increase — the
  record backlog is the marker (charter Part 17's worked example).
- **Unit economics, discriminator in practice** — merchant GPU rental: a $/GPU-hr figure falling
  faster than the next-best cloud alternative on the same metric supports "Very strong"; a $/GPU-hr
  figure merely moving in line with the market supports "Strong" at best.
- **Strategic risk, Strong** — a named circular-financing arrangement between a chipmaker and a
  customer that independent analysts have publicly flagged, with no enacted action yet: that is the
  "pending, publicly flagged" marker for "Strong," short of the "enacted, dated trigger" needed for
  "Very strong."
- **Momentum, Very strong (non-chip example)** — grid interconnection queues for new power
  generation stretching to a multi-year record while demand keeps arriving faster than plants can be
  hooked up: demand keeps arriving faster than the category can serve it, so the binding limit on
  the core quantity's growth is capacity, not demand.
