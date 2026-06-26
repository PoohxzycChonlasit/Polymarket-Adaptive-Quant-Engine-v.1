# Module Ownership Map 001

This map outlines the responsibilities, dependencies, and boundary couplings for the major modules in the quant engine.

---

## 1. `config/settings.py`
- **Owner Role:** `15_CONFIG_SAFETY_AGENT.md`
- **Responsibility:** Load, parse, and validate settings from `.env` and environment variables using Pydantic.
- **Inputs:** OS environment variables, local `.env` file.
- **Outputs:** Pydantic `Settings` instance.
- **Consumers:** Entire codebase (imported globally via `get_settings()`).
- **Producers:** Operating System.
- **Hidden Coupling:** High global coupling since settings dictate dry-run flags and API endpoints for all modules.
- **Boundary Violations:** None.

---

## 2. `polymarket/trader.py`
- **Owner Role:** `02_CODE_ARCHITECT_AGENT.md` (As God Object)
- **Responsibility:** Orchestrate scans, update bankroll state, run order matching/execution loops, track stats, and coordinate TP/SL exits.
- **Inputs:** `Settings`, CLOB price feeds, local position states.
- **Outputs:** Order submissions, local database updates, Rich display metrics.
- **Consumers:** `main.py`.
- **Producers:** `PolymarketClient`, price feeds, `OpportunityScanner`.
- **Hidden Coupling:** Deep dependency on nearly every single file in `polymarket/` and `utils/`.
- **Boundary Violations:** Formats UI metrics, manages file writes, and performs sizing mathematical overrides in-place.

---

## 3. `utils/risk_manager.py`
- **Owner Role:** `03_RISK_MANAGER_AGENT.md`
- **Responsibility:** Enforce hard risk limits (drawdown limits, cluster loss detection, mode gates).
- **Inputs:** Account balance, consecutive trade outcome records, current drawdown.
- **Outputs:** Risk mode transitions, allow/veto trading flags, `RiskPlan`.
- **Consumers:** `PolymarketTrader`.
- **Producers:** `PolymarketTrader` (which feeds trade results).
- **Hidden Coupling:** Coupled with the `BankrollState` data structures.
- **Boundary Violations:** None.

---

## 4. `utils/position_tracker.py`
- **Owner Role:** `06_POSITION_RECONCILIATION_AGENT.md`
- **Responsibility:** Maintain local accounting of open/closed positions, calculate unrealized PnL, and audit mismatches against CLOB.
- **Inputs:** Fill receipts, CLOB balances, oracle prices.
- **Outputs:** Position lists, PnL statistics, reconciliation mismatch reports.
- **Consumers:** `PolymarketTrader`, `RealtimeLogger`.
- **Producers:** `PolymarketTrader`.
- **Hidden Coupling:** Directly linked to database/disk schemas.
- **Boundary Violations:** None.

---

## 5. `polymarket/client.py`
- **Owner Role:** `05_MARKET_DATA_AGENT.md`
- **Responsibility:** Interface with the Polymarket CLOB REST and WebSocket endpoints for balance queries, orderbooks, and order placement.
- **Inputs:** Wallet keys, API credentials, order parameters.
- **Outputs:** Balance snapshots, bid/ask orderbooks, order execution receipts.
- **Consumers:** `PolymarketTrader`.
- **Producers:** Polymarket API.
- **Hidden Coupling:** Relies on third-party `py-clob-client` SDK internals.
- **Boundary Violations:** None.

---

## 6. `utils/quant_event_logger.py`
- **Owner Role:** `11_OBSERVABILITY_INCIDENT_AGENT.md`
- **Responsibility:** Append structured events sequentially into categorized JSONL log files.
- **Inputs:** Event name, raw data dictionary.
- **Outputs:** Disk JSONL files.
- **Consumers:** `PolymarketTrader`, `main.py`.
- **Producers:** Entire execution flow.
- **Hidden Coupling:** Generates unique session hashes that correlate traces.
- **Boundary Violations:** None.
