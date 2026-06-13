# Master Edge Taxonomy 001

Status: FROZEN CLASSIFICATION REFERENCE

## Purpose

The taxonomy assigns each candidate one primary edge class before analysis.
Secondary modifiers may be recorded, but they cannot replace the primary
decision-bearing hypothesis.

## A. Lead-Lag

Definition:

One observable market or feed changes before another price or probability
updates.

Examples:

- spot exchange move preceding Polymarket repricing;
- cross-venue orderbook movement preceding the target market.

Common false positives:

- timestamp skew;
- stale target quotes;
- shared reaction to a third source;
- unexecutable latency advantage.

Overlap risks:

Lead-lag can resemble settlement, momentum, or microstructure edge.

## B. Settlement

Definition:

Edge arising from the relationship between settlement rules, oracle state,
price-to-beat, and remaining time.

Examples:

- delayed settlement repricing;
- oracle print versus market-implied resolution probability.

Common false positives:

- misunderstood settlement source;
- stale oracle data;
- ambiguous event timing;
- resolution labels inferred from price rather than official truth.

Overlap risks:

Settlement can resemble lead-lag, time decay, or relative value.

## C. Behavioral

Definition:

Persistent participant behavior causes systematic overreaction,
underreaction, crowding, or side bias.

Examples:

- recurring YES preference;
- session-specific overreaction;
- repeated lifecycle-entry behavior.

Common false positives:

- selected historical slice;
- changing admission gates;
- regime concentration;
- repeated rows treated as independent observations.

Overlap risks:

Behavioral candidates often overlap with modifiers, time decay, and
microstructure.

## D. Microstructure

Definition:

Edge arising from orderbook mechanics, spread, depth, queue behavior, or
short-horizon repricing.

Examples:

- executable spread capture;
- depth imbalance followed by repricing;
- stale quote adverse-selection avoidance.

Common false positives:

- mid-price gains that are not executable;
- ignored queue position;
- missing fees or minimum-order constraints;
- partial-fill and liquidity assumptions.

Overlap risks:

Microstructure can resemble lead-lag or relative-value edge.

## E. Relative Value

Definition:

Mispricing between logically or economically related instruments.

Examples:

- YES and NO inconsistency;
- related market or maturity inconsistency;
- cross-market probability relationship.

Common false positives:

- non-synchronous quotes;
- incompatible settlement contracts;
- unavailable simultaneous execution;
- hidden liquidity constraints.

Overlap risks:

Relative value can resemble arbitrage, settlement, or lead-lag.

## F. Time Decay

Definition:

Predictable probability or price behavior driven by diminishing time to
resolution.

Examples:

- convergence toward terminal consensus;
- lifecycle-specific decay or repricing.

Common false positives:

- directional trend mistaken for decay;
- outcome-conditioned sampling;
- cutoff and admission effects;
- terminal price used without official resolution truth.

Overlap risks:

Time decay overlaps with settlement and lifecycle modifiers.

## G. Modifiers

Definition:

Variables that condition another edge but are not independently decision-bearing.

Examples:

- regime;
- session hour;
- liquidity state;
- quote freshness;
- lifecycle phase;
- balance or risk mode.

Common false positives:

- promoting a descriptive segment as an edge;
- post-hoc slicing;
- treating admission-policy effects as signal.

Overlap risks:

Modifiers can attach to every primary class. A modifier-only candidate must be
explicitly defined as a new primary hypothesis before promotion.

## Classification Rule

Each candidate receives:

- one primary class;
- zero or more documented modifiers;
- one frozen decision-bearing unit;
- one explicit null-suite mapping.
- one immutable candidate fingerprint.

Class changes after results are observed create a new candidate.

Reference controls, including the Null Suite, are not candidates and do not
belong to classes A-G.
