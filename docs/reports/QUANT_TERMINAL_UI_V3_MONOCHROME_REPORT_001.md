# QUANT_TERMINAL_UI_V3_MONOCHROME_REPORT_001.md

## Executive Summary
This report outlines the successful frontend UI redesign (`QUANT_TERMINAL_UI_V3_MONOCHROME_REDESIGN`) converting the Vite + React dashboard into a professional, institutional-grade monochrome trading terminal (inspired by Bloomberg, Jane Street, and HRT screens). The redesign increases information density, improves layout compactness, and strictly enforces monochrome color rules—reserving colors exclusively for alerts.

---

## Technical Specifications & Styling Rules
1. **Color Scheme**:
   - **Backgrounds**: True black (`#000000`) for pages, panels set to `#0a0a0a` and `#151515`, boundaries/scrollbars set to `#2a2a2a`.
   - **Borders**: Strictly `#2a2a2a` (slate-600 / border-slate-600 mapped variables).
   - **Text**: White (`#ffffff`) for active fields, light gray (`#d0d0d0`) for content, and muted gray (`#9a9a9a`) for secondary labels.
   - **Alerts**: Restricted to strict green (`#22c55e` - Success), amber (`#eab308` - Warning), and red (`#ef4444` - Critical).
2. **Typography**:
   - Monospace font (`font-mono`) applied to all numerical values, metric rows, table cells, and codes.
3. **Density**:
   - Eliminated SaaS card containers and wide margins.
   - Shifted to compact layouts, allowing major telemetry panels (Health, Portfolio, Signal Funnel, Risk, Alerts) to fit fully above the fold in a unified trading cockpit layout.

---

## Implemented Redesign Components

### 1. Bloomberg-Style Metric Rows
We implemented a dotted leader-line metric row layout (`BloombergMetricRow` in `MetricCard.tsx`) to replace boxy grids of cards.
- **Dotted Separator**: Label on the left and monospace value on the right, connected by a dotted line.
- **Density**: Stacked vertically, saving significant vertical screen space.
- **Affected Sections**:
  - `RuntimeHealthSection`
  - `RiskSection`
  - `PortfolioSection` (displayed in a high-density, two-column layout)
  - `StorageSection` (in compact mode on the Overview page)

### 2. Signal Pipeline Funnel
A horizontal visual conversion stepper was built in `SignalIntelligenceSection.tsx` utilizing `candidate_funnel_today` telemetry:
- **Steps**: `Decisions` ➔ `Signal Passed` ➔ `Risk Passed` ➔ `Entries`.
- **Logic**:
  - `Decisions`: Count of total evaluations.
  - `Signal Passed`: Decisions minus skips due to strategy/confidence/EV parameters.
  - `Risk Passed`: Signal Passed minus skips due to risk budget, exposure caps, cooldowns, or lockdown constraints.
  - `Entries`: Count of executed trade positions.
- **Visuals**: Styled in monospace border wrappers with arrows showing drop-off yield percentages.

### 3. Sidebar Future Expansion
- **Layout**: Expanded sidebar locked at `w-[160px]`.
- **Aesthetic**: Monochrome active highlight using borders and white texts.
- **Future Anchors**: Configured sub-links (`#replay`, `#session`, `#regime`, `#expectancy`, `#backtest`, `#monte-carlo`) under a new "Research Suite" heading. Clicking anchors dynamically navigates and focuses the respective workspace cards.

### 4. Quantitative Research Terminal
Replaced the single "coming soon" message with six fully developed mock quantitative workspaces:
1. **Replay Workspace (`#replay`)**: Displays replay stats (holding times, slippage, max DD) and a tabular order log (reload/unload decay, MAE/MFE).
2. **Session Workspace (`#session`)**: Tracks state transitions for the Quant Lifecycle Inventory System (`OPENING_SCAN` ➔ `ACTIVE_INVENTORY_TRADING` ➔ `PROFIT_MANAGEMENT` ➔ `FINAL_DERISK` ➔ `CLOSED_OR_UNSAFE`).
3. **Regime Workspace (`#regime`)**: Matrices for primary trend, volatility regimes, VPIN, and compression.
4. **Expectancy Workspace (`#expectancy`)**: Model parameters, probability floors, and pricing sweeps.
5. **Backtest Workspace (`#backtest`)**: Historical Sharpe, profit factor, drawdown, and CLI smoke run instructions.
6. **Monte Carlo Workspace (`#monte-carlo`)**: Percentile drawdown risks and Value at Risk (VaR) matrices.
- **Interactivity**: Built React `useEffect` hash listeners. Clicking sidebar anchors scrolls the page and flashes the focused panel border with a white highlight.

### 5. Storage Page Archival Telemetry
- **Compact overview**: Replaced the large storage box on the Overview dashboard with three simple Bloomberg-style rows (Quant Data Total, Candidates, Reclaimable GB).
- **Expanded page**: Surfaced rich compression and archive telemetry available from the dashboard state:
  - Algorithm used (`gzip`) and age threshold (e.g., 7 days).
  - Compression candidate file count and expected reclaimable space formatted to GB.
  - Path of the dry-run compression manifest.
  - Compress/Restore verification pass/fail status flags.
  - Storage categories Recharts bar chart styled in neutral gray-scale colors.
  - Category details datatable with file count, gz count, size, and latest filenames.

---

## Verification Summary
- **Compilation**: Production bundle compiled successfully with `npm run build` (`dist/assets` output files generated, zero TypeScript compiler errors).
- **Unit Tests**: Executed `npm run test:run`. All 12 unit tests passed successfully.
- **Modifications**: All updates restricted to the `dashboard/` directory. Zero changes made to python files or live sizing configs.
