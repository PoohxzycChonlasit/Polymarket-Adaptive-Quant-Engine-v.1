# TASK_REQUEST.md

# Current Task

## Fix and harden paper-mode balance visibility.

# Goals

- paper mode must correctly see available balance
- paper mode may read live wallet balance ONCE at startup as reference only
- paper mode must use paper_virtual_cash afterward
- risk sizing must never silently become zero
- all no-entry reasons must be visible in logs

---

# Constraints

Do NOT:

- loosen strategy thresholds
- disable risk controls
- remove stale data protections
- inspect unrelated runtime files
- inspect historical logs
- rewrite architecture

---

# Relevant Areas

- paper wallet
- virtual balance
- risk sizing
- runtime config
- startup initialization
- decision logging

---

# Ignore Areas

- archived logs
- parquet files
- historical reports
- unrelated tests
- dashboard/ui modules

---

# Success Criteria

Success means:

- paper mode sees usable balance
- order size no longer silently becomes zero
- startup logs clearly show paper balance state
- no-entry diagnostics explain sizing failures
- no repeated live wallet polling every decision tick
