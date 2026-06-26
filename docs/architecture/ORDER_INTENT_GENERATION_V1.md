# ORDER_INTENT_GENERATION_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the Order Intent Generation layer for the Polymarket Crypto 5M Quant Engine execution interface. It defines the datastructure and validation checks applied before order submission.

---

## 1. The OrderIntent Structure

The `OrderIntent` is an immutable, frozen data structure that encapsulates all sizing, pricing, and safety properties calculated by the decision pipeline:

| Property | Data Type | Purpose |
| :--- | :---: | :--- |
| **`intent_type`** | `OrderIntentType` | `ENTRY` (Buy) or `EXIT` (Sell). |
| **`token_id`** | `str` | The Polygon contract address for the YES or NO token. |
| **`side`** | `str` | `BUY` or `SELL`. |
| **`price`** | `float` | The execution price limit ($0.01 to $0.99). |
| **`size`** | `float` | The quantized share count (integer value). |
| **`market_id`** | `str` | The Polymarket market UUID. |
| **`outcome`** | `str` | `YES` or `NO`. |
| **`position_id`** | `str` | Local database reference ID. |
| **`risk_approved`** | `bool` | Set to True only if the **Risk Budget Engine** approved the trade. |
| **`reconciliation_safe`** | `bool` | Set to True only if the **Position Manager** confirmed zero imbalances. |
| **`lockdown_active`** | `bool` | Set to True if the state machine is in `LOCKDOWN`. |
| **`tracked_inventory_size`**| `float` | Local tracked share count for that position (for exit size validation). |

---

## 2. Order Intent Validation Logic

Before the intent is sent to the network client, the engine executes `validate_order_intent(intent)` to perform final sanity checks:

```
                            OrderIntent Generated
                                      │
                                      ▼
                      Basic Sanity: Is side in {BUY, SELL}?
                     Does token_id exist? Is size > 0?
                     Is price in range (0.0, 1.0)?
                                      ├──► NO  ──► REJECT (invalid_side/price/size)
                                      └──► YES
                                           │
                                           ▼
                                 [Check Intent Type]
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
                 [ENTRY]                                       [EXIT]
                    │                                             │
      - Is side == BUY? (No shorting)              - Is side == SELL? (No exit buying)
      - Is lockdown_active == False?               - Is position_id present?
      - Is reconciliation_safe == True?            - Is tracked_inventory_size > 0?
      - Is risk_approved == True?                  - Is size <= tracked_inventory_size?
      - Is outcome in {YES, NO}?                   (Prevent naked selling/over-selling)
                    │                                             │
      ┌─────────────┴─────────────┐                 ┌─────────────┴─────────────┐
      ▼                           ▼                 ▼                           ▼
    FAIL                        PASS              FAIL                        PASS
      │                           │                 │                           │
    REJECT                      APPROVE           REJECT                      APPROVE
```

---

## 3. Packaging & Handoff to Execution Client

1. **Successful Validation**:
   - If `validate_order_intent` returns `approved = True`, the `OrderIntent` is passed directly to the CLOB order submission function:
     $$\text{Execution Receipt} = \text{place\_order}(\text{OrderIntent})$$
   - In paper mode, this logs `order_intent_approved` and generates a synthetic fill receipt. In live mode, it signs and submits the Polygon transaction.
2. **Blocked Validation**:
   - If validation returns `approved = False`, the engine raises an `ORDER_INTENT_BLOCKED` warning. No bytes are sent to the network.
   - The engine logs the failure reason (e.g. `sell_without_tracked_inventory` or `risk_plan_not_approved`) to the JSONL decision log, and triggers a Telegram incident alert.
