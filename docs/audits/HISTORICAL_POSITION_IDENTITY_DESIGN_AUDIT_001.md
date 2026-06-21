# HISTORICAL_POSITION_IDENTITY_DESIGN_AUDIT_001

## 1. Why Current Identity Fails
The current execution position linkage fails in historical paper mode because it resolves position identity using `execution_position_id` or `order_id` alone. 

In `paper` mode, the bot generates simulated order IDs by extracting the first 8 characters of the YES/NO token ID and prepending `"paper-"` (e.g. `paper-71824750`). When multiple concurrent runs or restarts trade the same contract (as occurred on **May 22, 2026**), they generate identical order IDs. Using these field values alone creates duplicate resolved execution position IDs (e.g. `ep_paper-71824750`), resulting in a `duplicate_open` `ReconciliationError` during historical replays.

---

## 2. Candidate Identity Keys Evaluation

| Option | Key Formula | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **A** | `position_id` only | Clean, standard production ID. | Often `null` or missing in older paper-era logs. |
| **B** | `execution_position_id` only | Explicit for execution records. | Often `null` in older logs; suffers from order ID collision when derived. |
| **C** | `order_id` only | Direct lookup key. | Collides in paper mode across parallel process runs. |
| **D** | `run_id + order_id` | Uniquely identifies order within a run. | Fails if `order_id` itself is missing in legacy schemas. |
| **E** | `run_id + execution_position_id` | Unique to the execution run. | Often `null` in older logs, preventing linkage. |
| **F** | `run_id + condition_id + asset + outcome + timestamp` | High specificity. | Close events have different timestamps than opens, so hashes do not match. |
| **G** | `source_file + line + event_sha256` | Guaranteed unique log line. | Cannot be referenced by close events to establish linkage. |
| **H** | **`historical_position_uid` (Dynamic)** | Flexible, robust, handles all eras. | Requires a stateful matching register during replay. |

---

## 3. Recommended Key
We recommend generating a **`historical_position_uid`** at the time of position opening:

$$\text{historical\_position\_uid} = \text{sha256}(\text{run\_id} + \text{resolved\_order\_id} + \text{condition\_id} + \text{asset} + \text{outcome} + \text{open\_timestamp\_utc})$$

### Verification against Data
This key resolves collisions because the `run_id` isolates concurrent parallel runs, and the `open_timestamp_utc` provides sub-second uniqueness. 
* For Line 1 (Open A): `sha256("20260521T133858Z_..." + "paper-71824750" + ... + "2026-05-22T02:35:25.555854Z")`
* For Line 2 (Open B): `sha256("20260521T044143Z_..." + "paper-71824750" + ... + "2026-05-22T02:35:28.667052Z")`

These generate two distinct, non-colliding UUID hashes.

---

## 4. Open/Close Matching Rules
To link opens and closes under this identity scheme:

1. **Modern Mode**: Use the canonical `position_id` if present and reliable.
2. **Historical Mode**:
   - Establish `historical_position_uid` on `trade_open` and store the position in an active registry.
   - When a `trade_close` event is processed:
     - **Rule A (Primary)**: Match by `(run_id, resolved_order_id)` if `resolved_order_id` is present.
     - **Rule B (Fallback)**: If `resolved_order_id` is missing (Generation A), match by `(run_id, condition_id, asset, outcome)` using FIFO (First In, First Out).
     - **Rule C (Ambiguity Protection)**: If multiple open candidates match the criteria, fail closed (raise `ReconciliationError: ambiguous_position_match`).

---

## 5. Collision Audit Results
We audited all 40 trade journal logs (`runtime/quant_data/trade_journal/*.jsonl`):

* **Total Open Events**: 732
* **Total Close Events**: 1,625
* **Collisions under `order_id` only**: 21
* **Collisions under `run_id + order_id`**: 0
* **Collisions under `run_id + condition_id + asset + outcome + timestamp`**: 0
* **Unresolved Closes (Simulated Replay)**:
  - **All Historical Files**: 894 unresolved closes (due to Generation A close-only logs).
  - **Post-May-18 Era (All)**: 366 unresolved closes (due to mock test logs written by the test suite).
  - **Post-May-18 Era (Excluding Mock Test Logs)**: **0 unresolved closes**. Every real close matched its open cleanly.

---

## 6. Replay Patch Recommendation
**A. Replace historical mode identity resolver only** (specifically within `tools/execution_paper_runtime.py`).

Since `--compat-mode` is already implemented and validated, we should update the position resolver inside `--compat-mode historical` to use the `(run_id, resolved_order_id)` mapping registry, avoiding the need for a new flag or preprocessing.

---

## 7. Tests Required
We need the following unit tests to validate the position identity model:
1. `test_two_opens_same_order_id_different_run_id_do_not_collide`
2. `test_open_close_same_run_id_order_id_match`
3. `test_same_order_id_same_run_id_duplicate_fails`
4. `test_missing_order_id_fallback_fifo_works`
5. `test_ambiguity_fails_closed`
6. `test_modern_position_id_path_unchanged`

---

## 8. Final Verdict

**READY_FOR_IDENTITY_PATCH**
