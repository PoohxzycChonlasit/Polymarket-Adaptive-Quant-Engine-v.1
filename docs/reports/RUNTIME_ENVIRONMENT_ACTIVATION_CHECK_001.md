# RUNTIME_ENVIRONMENT_ACTIVATION_CHECK_001

**Date:** 2026-06-26  
**Purpose:** Verify desktop environment can run the project after notebook → desktop migration  
**Predecessor:** PROJECT_HEALTH_CHECK_001 (repo healthy, import smoke failed due to missing pydantic in system Python)

---

## 1. Python Executable

| Item | Value |
|------|-------|
| Active Python (`where python`) | `C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\python.exe` |
| Version | Python 3.12.10 |
| Other Python on PATH | `C:\Users\POOHXYZ\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe` (hermes agent — unrelated) |
|  | `C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python311\python.exe` (Python 3.11 — not used) |
| System Python has pydantic? | NO — bare system Python lacks all project dependencies |

---

## 2. Venv Status

Three venv-related folders found in project root:

### `.venv` — BROKEN (wrong-user path mismatch)

```
pyvenv.cfg:
  home = C:\Users\poh_2\AppData\Local\Programs\Python\Python312
  version = 3.12.10
  executable = C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe
```

- Created on the **notebook** under user `poh_2`
- Desktop user is `POOHXYZ` — the `poh_2` path does not exist here
- `.venv\Scripts\python.exe` fails: `No Python at 'C:\Users\poh_2\...'` (exit 103)
- The `Scripts/activate` and `Activate.ps1` scripts set PATH to `.venv\Scripts\`, but the Python launcher in that folder fails
- **Lib/site-packages is intact**: 297 packages installed, including all project dependencies

### `.venv_BROKEN_poh2_py312_backup` — BROKEN (same issue)

```
pyvenv.cfg:
  home = C:\Users\poh_2\AppData\Local\Programs\Python\Python312
  version = 3.12.10
```

- Explicitly named as broken; same poh_2 path mismatch
- Contains same site-packages (backup copy from before or during the machine move)

### `venv/` — EMPTY

- Directory exists but contains no files
- Not usable

---

## 3. Dependency Check

The `.venv\Lib\site-packages` directory contains 297 installed packages.  
Even though the venv launcher is broken, the packages are accessible via `PYTHONPATH`.

Test: `PYTHONPATH=.venv/Lib/site-packages python -c "import pydantic; print(pydantic.__version__)"`

| Package | Result | Version |
|---------|--------|---------|
| `pydantic` | **PASS** | 2.12.5 |
| `pydantic_settings` | **PASS** | present |
| `py_clob_client` | **PASS** | 0.34.6 |
| `py_order_utils` | **PASS** | 0.3.2 |
| `aiohttp` | **PASS** | 3.14.1 |
| `websockets` | **PASS** | present |

All core runtime dependencies are present in `.venv/Lib/site-packages`.

---

## 4. Trader Import Result

Test: `PYTHONPATH=.venv/Lib/site-packages python -c "from polymarket.trader import PolymarketTrader; print('TRADER_IMPORT_OK')"`

```
TRADER_IMPORT_OK
```

**PASS** — PolymarketTrader imports cleanly when PYTHONPATH points to the intact site-packages.

---

## 5. Root Cause Summary

The venv was created on the notebook under user `poh_2`. After moving to the desktop (`POOHXYZ`), the venv launcher executables in `.venv\Scripts\` reference hardcoded absolute paths to `C:\Users\poh_2\...` which do not exist. The Python launcher exits 103. However:

- The desktop has Python 3.12.10 installed at `C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\`
- The `.venv\Lib\site-packages` directory is fully intact with all 297 packages
- All imports succeed when the system Python is given `PYTHONPATH` pointing to the intact site-packages

**Permanent fix required (not done yet):** The venv must be recreated using the desktop's Python (`POOHXYZ` user path) against the existing `requirements.txt`. This is a one-time operation that will make activation work normally.

---

## 6. Runtime Readiness Verdict

The venv launcher is broken, but runtime is reachable via `PYTHONPATH` workaround.  
This is sufficient to run paper mode safely without creating a new venv.

---

## 7. Exact Command to Activate Runtime (Workaround)

Use this exact command prefix for all Python invocations until the venv is rebuilt:

```powershell
# PowerShell — set once per session
$env:PYTHONPATH = "C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\.venv\Lib\site-packages"
python main.py --mode paper --interval 60 --ui auto --fps medium
```

```bash
# Git Bash — set once per session
export PYTHONPATH="C:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.venv/Lib/site-packages"
python main.py --mode paper --interval 60 --ui auto --fps medium
```

Or inline without session state:

```bash
PYTHONPATH="C:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.venv/Lib/site-packages" python main.py --mode paper
```

**For tests:**

```bash
PYTHONPATH="C:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.venv/Lib/site-packages" python -m pytest tests/ -q
```

---

## 8. Permanent Fix (When Ready — Do Not Run Now)

```powershell
# 1. Remove broken venv
Remove-Item -Recurse -Force "C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\.venv"

# 2. Create fresh venv with correct Python
C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv

# 3. Activate and install from requirements.txt
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

After this, normal `.venv\Scripts\Activate.ps1` activation will work without any PYTHONPATH override.

---

## 9. Requirements File

`requirements.txt` — present in project root. Will be used for venv rebuild when authorized.

---

## Final Verdict

```
RUNTIME_BLOCKED_BAD_VENV
```

**Detail:** Venv exists and contains all packages, but the launcher is broken due to user-path mismatch (notebook `poh_2` → desktop `POOHXYZ`). Runtime is accessible via `PYTHONPATH` workaround — all imports pass, PolymarketTrader loads. A venv rebuild is the permanent fix; it is not executed yet per task scope.

**Safe to run paper mode with PYTHONPATH workaround:** YES  
**Safe to start Batch 2 planning:** YES  
**Permanent fix needed before normal workflow:** YES — venv rebuild
