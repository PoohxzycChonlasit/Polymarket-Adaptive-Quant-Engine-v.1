# Paper Process Cleanup Audit

Date: 2026-05-25 18:30 Asia/Bangkok

Scope: process-state cleanup for paper evidence hygiene. No code, strategy, risk, execution, field wiring, or live changes.

## Goal

Make evidence collection cleaner by ensuring only one clearly active paper bot runtime remains.

Known latest active evidence:

- run_id: `20260525T065423Z_53560_1b672958`
- active Python PID: `53560`
- active launcher PID: `57084`
- command: `main.py --mode paper --interval 10 --ui compact --fps medium`

## Processes Before

`Get-Process python | Select-Object Id, StartTime, CPU, Path`

| PID | Start Time | CPU | Path |
|---:|---|---:|---|
| 25112 | 2026-05-19 19:44:44 | 31.890625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 1392 | 2026-05-19 19:58:19 | 32.078125 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 28108 | 2026-05-19 20:22:17 | 31.1875 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 18068 | 2026-05-19 20:59:49 | 32.140625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 48012 | 2026-05-20 13:22:07 | 1319.796875 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 13704 | 2026-05-21 11:41:38 | 11739.15625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 31032 | 2026-05-22 12:26:08 | 3845.9375 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 13912 | 2026-05-22 12:58:26 | 3768.78125 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 26740 | 2026-05-22 14:56:52 | 3283.0625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 46088 | 2026-05-22 16:42:08 | 2745.65625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 53560 | 2026-05-25 13:54:17 | 1934.21875 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |
| 51368 | 2026-05-25 17:40:16 | 561.40625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` |

Command-line inspection was used to avoid stopping unrelated Python apps.

## Process Classification

Kept:

| PID | Process | Reason |
|---:|---|---|
| 53560 | `python.exe` | newest active paper runtime, matches known latest evidence run |
| 57084 | `py.exe` | launcher for active paper runtime |
| 25112 | `python.exe` | `hermes_worker.py --dashboard-web --web-port 8499`, not paper bot |
| 1392 | `python.exe` | `hermes_worker.py --dashboard-web --web-port 8498`, not paper bot |
| 28108 | `python.exe` | `hermes_worker.py --dashboard-web --web-port 8497`, not paper bot |
| 18068 | `python.exe` | `hermes_worker.py --dashboard-web --web-port 8496`, not paper bot |
| 48012 | `python.exe` | `python.exe -m unittest tests.test_research_scheduler_runtime -v`, not paper bot |
| 51368 | `python.exe` | `hermes_worker.py --live --telegram --open-browser ...`, not paper bot |

Stopped:

| PID | Process | Command | Why Safe |
|---:|---|---|---|
| 28012 | `py.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper launcher older than active PID 53560 |
| 13704 | `python.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper bot from 2026-05-21 |
| 52644 | `py.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper launcher older than active PID 53560 |
| 31032 | `python.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper bot from 2026-05-22 |
| 13912 | `python.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper bot from 2026-05-22 |
| 26740 | `python.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper bot from 2026-05-22 |
| 46088 | `python.exe` | `main.py --mode paper --interval 10 --ui compact --fps medium` | stale paper bot from 2026-05-22 |

Stop command used:

```powershell
Stop-Process -Id 28012,13704,52644,31032,13912,26740,46088 -Force -ErrorAction SilentlyContinue
```

## Processes After

`Get-Process python | Select-Object Id, StartTime, CPU, Path`

| PID | Start Time | CPU | Path | Classification |
|---:|---|---:|---|---|
| 25112 | 2026-05-19 19:44:44 | 31.890625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | Hermes dashboard, left running |
| 1392 | 2026-05-19 19:58:19 | 32.078125 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | Hermes dashboard, left running |
| 28108 | 2026-05-19 20:22:17 | 31.1875 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | Hermes dashboard, left running |
| 18068 | 2026-05-19 20:59:49 | 32.140625 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | Hermes dashboard, left running |
| 48012 | 2026-05-20 13:22:07 | 1319.859375 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | unittest process, left running |
| 53560 | 2026-05-25 13:54:17 | 1936.21875 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | active paper bot, kept |
| 51368 | 2026-05-25 17:40:16 | 561.921875 | `C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe` | Hermes live/telegram worker, left running |

Command-line re-check after cleanup:

- only one `main.py --mode paper --interval 10 --ui compact --fps medium` Python runtime remains: PID `53560`.
- only one matching `py.exe` launcher remains: PID `57084`.
- all stopped stale paper bot PIDs disappeared from the process list.

## Evidence Hygiene Result

Before cleanup, multiple stale paper runtimes were still writing paper bot logs and could contaminate day-level JSONL evidence.

After cleanup, current paper evidence should be cleaner:

- active paper bot runtime kept: PID `53560`
- active paper launcher kept: PID `57084`
- stale paper bots stopped: `13704`, `31032`, `13912`, `26740`, `46088`
- stale paper launchers stopped: `28012`, `52644`
- unrelated Python apps left untouched

Research caveat:

Historical files for `2026-05-25` may still contain pre-cleanup multi-process evidence. Post-cleanup claims should filter by timestamp and `run_id`, especially around the cleanup boundary.

## Final Status

Files created:

- `docs/research/paper_process_cleanup_audit.md`

Runtime behavior changed: No, process cleanup only

Live behavior changed: No

Strategy/risk/execution changed: No

Code changed: No

Tests run: none; process cleanup and docs-only audit.
