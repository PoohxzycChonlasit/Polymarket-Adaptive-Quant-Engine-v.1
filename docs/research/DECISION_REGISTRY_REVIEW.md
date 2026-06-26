# DECISION_REGISTRY_REVIEW

This document evaluates the status of `DEC_2026_06_18_SHADOW_SIZER_DESIGN` under the active question `LOW_PRICE_TRUTH_RESOLUTION_001`.

## Recommendation
**Keep the shadow sizer design decision in `PROPOSED` status.** Do NOT remove it.

## Rationale
1. **Lineage Preservation**: Removing the entry from the registry completely would hide the fact that a shadow sizer design has already been drafted and reviewed. Keeping it as `PROPOSED` preserves the history of the design.
2. **Explicit Block State**: Under the *Active Question System V1*, any decision in `PROPOSED` status is strictly blocked from runtime implementation. This ensures safety without deleting development records.
3. **Transition Trigger**: Once the active question `LOW_PRICE_TRUTH_RESOLUTION_001` is closed:
   - If the verdict is `EDGE_REAL`, the decision will be promoted to `ACTIVE` (with operator approval).
   - If the verdict is `REPLAY_ARTIFACT`, the decision will be moved to `REJECTED`.
   Keeping the entry as `PROPOSED` maintains a clear transition path for when the active question is resolved.
