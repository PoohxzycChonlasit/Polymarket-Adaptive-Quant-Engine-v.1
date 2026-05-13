# Bounded Multi-Price Inventory Engine

> Status: Phase 3 design target, not implemented runtime behavior.
> Scope: future controlled inventory architecture. This document is not permission to trade multiple entries.

## Purpose

Define the safe destination for future inventory-based Polymarket trading after Phase 1 probability diagnostics and Phase 2 replay research provide enough evidence.

## Core Principle

Inventory trading is allowed only when it is bounded. It must never become martingale, unlimited averaging down, all-in behavior, or loss-chasing.

## Required Runtime Guards Before Implementation

- max inventory cap
- max notional cap
- max risk cap
- max reload count
- minimum time remaining
- liquidity and spread quality gates
- stale-book protection
- stop loss
- forced exit
- panic exit
- reconciliation gate
- OrderIntent validation
- paper/live separation

## Future Inventory Actions

Allowed only after explicit implementation scope:

- starter buy
- limited reload
- partial unload
- runner hold
- forced flatten

Forbidden:

- martingale
- infinite averaging down
- increasing size because of losses
- live multi-entry without paper validation
- bypassing risk or reconciliation

## Required Evidence Before Runtime Work

- repeated paper-session replay evidence
- regime-specific opportunity table
- MFE/MAE table
- spread/liquidity feasibility table
- bankroll sensitivity table
- clear failure-mode analysis

## Agent Ownership

Primary:

- `20_INVENTORY_ENGINE_AGENT.md`

Supporting:

- `03_RISK_MANAGER_AGENT.md`
- `04_EXIT_EXECUTION_AGENT.md`
- `06_POSITION_RECONCILIATION_AGENT.md`
- `22_INVENTORY_ANALYTICS_AGENT.md`

