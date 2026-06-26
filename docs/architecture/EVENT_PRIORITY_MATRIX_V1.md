# Event Priority & Frequency Matrix V1

This document defines the classification of events in the **Runtime Event Stream V1** based on frequency, bandwidth footprint, and importance.

---

## Event Classification

Events are classified into three priority bands: **CRITICAL**, **MEDIUM**, and **BACKGROUND**.

| Event Type | Priority Band | Est. Frequency | Volume (per hour) | UI Rendering Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `heartbeat` | **CRITICAL** | Fixed 5s | 720 | Instant repaint / status bar pulse |
| `entry_submitted` | **CRITICAL** | On Execution | Low (0-20) | Modal highlight / immediate update |
| `entry_filled` | **CRITICAL** | On Execution | Low (0-20) | Active position list repaint |
| `exit_submitted` | **CRITICAL** | On Execution | Low (0-20) | Alert notification / order list |
| `exit_filled` | **CRITICAL** | On Execution | Low (0-20) | Position removal / PnL update |
| `risk_state_changed` | **CRITICAL** | On Transition | Low (<5) | Red banner lockdown mode warning |
| `ghost_position_detected` | **CRITICAL** | Startup Only | Very Low (0-5) | Operational quarantine table log |
| `candidate_ranked` | **MEDIUM** | Once per cycle | Medium (240) | Grid sorting repaint |
| `bankroll_changed` | **MEDIUM** | Once per cycle | Medium (240) | Rolling balance charts repaint |
| `inventory_changed` | **MEDIUM** | Once per cycle | Medium (240) | Position sizing charts update |
| `candidate_found` | **BACKGROUND** | Once per cycle | High (1,000+) | Cached list (no instant repaint) |
| `candidate_rejected` | **BACKGROUND** | Once per cycle | High (1,000+) | Silent log panel update |
| `analytics_loaded` | **BACKGROUND** | Once per cycle | Medium (240) | Background metrics refresh |

---

## Performance & Optimization Guidelines

### High-Volume Throttling
- **`candidate_found` and `candidate_rejected`**: Since these events occur at high frequency during scanner cycles, the dashboard consumer should buffer these events and perform single-batch DOM repaints (every 1-2 seconds) rather than rendering each event individually. This prevents UI freeze.

### Storage Compression
- **`BACKGROUND` Priority logs**: Since candidate rejections can populate large log files over a 24-hour run, the `QuantEventLogger` should separate background-priority scan metrics into dedicated telemetry buckets, allowing operators to configure automatic truncation or disable writing them to disk during low-disk shadow campaigns.
