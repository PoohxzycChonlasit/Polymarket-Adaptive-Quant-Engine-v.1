# Runtime Event Stream Design Report

This report presents the system design and implementation plan for the **Runtime Event Stream V1** to support real-time dashboard visualization.

---

## 1. Architecture Overview

The event stream design transitions the quant trading bot from an active-polling model to a push-based, event-driven model. The core design uses a **File-Backed JSONL Event Stream** that writes serialized event envelopes to disk in real-time. This eliminates networking dependencies inside the execution loop, preserving 100% of the safety guarantees required for high-frequency scanning.

- **Producer**: `PolymarketTrader` triggers event emission via a synchronized, thread-safe `QuantEventLogger`.
- **Stream Store**: Append-only Line-Delimited JSON (`.jsonl`) logs, optimized by OS page caching.
- **Consumer**: A tail-based log reader (located in the dashboard/API process) that processes events asynchronously.

---

## 2. Event Taxonomy

Events are categorized into distinct operational layers:

1. **System & Process**:
   - `heartbeat`: Heartbeat tick containing bot health and process stats (every 5 seconds).
   - `runtime_health_changed`: Signals API connection issues or circuit-breaker status.
   - `ghost_position_detected` / `ghost_position_sentinel_summary`: Sentinel diagnostics.
2. **Scanner & Candidates**:
   - `candidate_found` / `candidate_rejected`: High-frequency scanner evaluation events.
   - `candidate_ranked`: Ordered list of candidates.
3. **Risk & Sizing**:
   - `risk_state_changed`: Drawdown warnings or lockdown activation.
   - `bankroll_changed`: Cash and equity metrics updates.
   - `inventory_changed`: Position tracker balance changes.
4. **Execution**:
   - `entry_submitted` / `entry_filled`: Position opening tracking.
   - `exit_submitted` / `exit_filled`: Position exit execution.
   - `trade_closed`: Final trade settlement containing realized PnL.

---

## 3. Heartbeat Design

The heartbeat runs on a strict **5-second timer** in the trader's outer execution loop. It contains:
- **Liveness Indicators**: `runtime_alive: true` and `uptime_seconds`.
- **System Metrics**: CPU utilization (%), memory utilization (MB), and event emission rates (EPS).
- **Portfolio Snapshots**: Virtual or live cash balance, current exposure, realized/unrealized PnL, drawdown, and bankroll tier.
- **State Indicators**: Risk modes (`NORMAL`, `DEFENSIVE`, `LOCKDOWN`), sizing multipliers, and active position details.

---

## 4. Replay Strategy & Checkpointing

- **Log-Reader Replay**: Reconnecting consumers query their last successfully processed `sequence_number` (checkpoint `N`).
- **State-Only Replay**: On startup or recovery, the consumer fast-forwards through historical events in the active `.jsonl` file, processing only stateful execution and risk events while skipping high-frequency candidate events.
- **Tail Mode**: Once the reader catches up to the current end-of-file, it watches for new line appends in real-time.

---

## 5. Ordering Guarantees

- **Single Sequencer**: The `QuantEventLogger` coordinates all writes using a thread lock (`threading.Lock`), ensuring events are serialized in strict chronological order.
- **Monotonic Sequence Numbers**: Every event has a 1-indexed, monotonically increasing sequence number per runtime session. A change in `runtime_session_id` indicates a session reset, restarting the sequence numbers.

---

## 6. Performance Considerations

- **Write Overhead**: Serializing small JSON payloads and flushing them to a local SSD takes <1ms, introducing negligible latency to the 1-second/60-second trader cycles.
- **Disk I/O Cache**: The OS filesystem cache buffers writes, preventing disk write blockages from stalling the trading loop.
- **Consumer isolation**: Dashboard parsing errors or network disconnections have 0% impact on trading loop throughput.

---

## 7. Recommended Implementation Roadmap

1. **Step 1: QuantEventLogger Expansion**
   - Update `utils/quant_event_logger.py` to register and implement logging methods for `log_ghost_position_detected_v1`, `log_ghost_position_sentinel_summary_v1`, `log_ghost_position_detected_v1`, and `log_ghost_position_sentinel_summary_v1`.
2. **Step 2: Heartbeat Generator**
   - Implement `emit_heartbeat()` in `PolymarketTrader` using `psutil` for system metrics.
3. **Step 3: Outer Loop Integration**
   - Update the realtime loop in `main.py` to trigger the heartbeat every 5 seconds.
4. **Step 4: Tail Reader Utility**
   - Create a clean python utility under `tools/` that demonstrates tailing the active JSONL file, parsing sequence numbers, and performing fast-forward replay.
5. **Step 5: Regression Tests**
   - Write unit tests verifying sequence increments, session resets, and schema validation.

---

## 8. Final Verdict

### `READY_FOR_IMPLEMENTATION`

The design is fully consistent with the quant engine's architecture freeze guidelines and provides a clean, decoupled, high-performance foundation for the dashboard UI.
