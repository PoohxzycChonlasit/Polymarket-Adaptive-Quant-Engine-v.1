# Event Replay Architecture V1

This document defines the replayability, state reconstruction, and ordering guarantee design for the **Runtime Event Stream V1**.

---

## The Replay Model

Every event written to the append-only JSONL log represents a state transition. By processing all events from sequence number `1` forward, a consumer can reconstruct the exact state of the runtime (Event Sourcing).

```text
               Event Stream (JSONL) on Disk
  +------------------+------------------+------------------+
  | Sequence: 1      | Sequence: 2      | Sequence: 3      |
  | type: bankroll   | type: entry_sub  | type: entry_fill |
  | cash: $100.00    | order_id: 101    | order_id: 101    |
  +------------------+------------------+------------------+
                            |
                            | (Replay Engine)
                            v
              Stateful Reconstruction (Memory)
  +--------------------------------------------------------+
  | Cash Balance: $100.00 -> $47.00                        |
  | Open Positions: [pm-5m-btc (size: 100, price: 0.53)]   |
  +--------------------------------------------------------+
```

---

## State Reconstruction on Reconnect

When a dashboard UI or monitoring tool disconnects and reconnects:

1. **Get Local Checkpoint**: The consumer checks its database or in-memory state for the last processed sequence number (`N`).
2. **Scan Log File**:
   - The reader opens the current JSONL log file.
   - It reads line-by-line, parsing the JSON envelope.
   - It filters out all events where `sequence_number <= N`.
3. **Optimized Replay**:
   - The consumer only executes state-modifying logic for stateful events (`entry_submitted`, `entry_filled`, `exit_submitted`, `exit_filled`, `risk_state_changed`, `bankroll_changed`).
   - It skips high-frequency transient events (`candidate_found`, `candidate_rejected`) to catch up to the tail immediately.
4. **Tail Mode**: Once the reader reaches the end of the file, it switches to tail mode, waiting for new lines to be appended and flushed by the runtime.

---

## Event Sequencing & Integrity

- **Monotonic Sequence Numbers**: The `QuantEventLogger` guarantees that sequence numbers increase by exactly 1 (`1, 2, 3...`) for the duration of a single `runtime_session_id`.
- **Write Thread Safety**: All event writes occur within a synchronization lock:
  ```python
  with self._lock:
      self._write_to_file(serialized_json_line)
  ```
  This ensures that there is never a race condition where sequence `M` is written to disk after sequence `M+1`.
- **Session Boundaries**: Upon process restart, a new `runtime_session_id` is generated, and sequence numbers reset to `1`. The consumer identifies this shift by detecting a change in the `runtime_session_id` property.
