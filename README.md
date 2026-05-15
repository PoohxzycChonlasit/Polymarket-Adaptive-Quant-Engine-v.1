# 🧠 PolyTrade Bot

> **Polymarket 5-Minute BTC/ETH Quant Research System**
> ระบบเทรดเชิงวิจัยสำหรับตลาด Binary Prediction 5 นาทีของ Polymarket
> สถานะปัจจุบัน: **Paper-first · Observability-first · Not live-trading ready**

---

## ⚠️ สถานะความจริงของโปรเจกต์

โปรเจกต์นี้ **ยังไม่ใช่ระบบ live trading ที่พร้อมใช้งานจริง** และ README นี้ตั้งใจเขียนให้ตรงกับหลักฐานล่าสุด ไม่อ้างกำไร ไม่อ้าง production HFT และไม่อ้างว่าระบบเทรดอัตโนมัติสำเร็จแล้ว

| หมวด | สถานะจริง |
|---|---|
| Runtime หลัก | Python Polymarket 5M bot |
| ค่าเริ่มต้น | Paper mode |
| Market data | ใช้ real market data / orderbook จริง |
| Execution | จำลองใน paper mode เป็นหลัก |
| Live mode | มี preflight แต่ยังไม่พร้อมใช้งานจริง |
| Current investigation | Runtime timing / cadence และ cutoff pressure |
| Latest scoped evidence | `20260515T143223Z_22760_1b6c0b35` |
| Root cause ล่าสุด | `cutoff` / `time_unsafe` |
| Secondary blocker | `risk_plan_zero` |
| Execution verdict | **Execution is not root cause** สำหรับ run ล่าสุด เพราะไม่มี true submit/fill/cancel attempt |
| Risk philosophy | Bounded risk, no martingale, no averaging down แบบไม่จำกัด |

> ระบบนี้ควรถูกมองเป็น **quant research + paper validation platform** ก่อน ไม่ใช่เครื่องพิมพ์เงิน ไม่ใช่ live bot ที่พร้อมยิง order จริง

---

## 🌟 Project Vision

PolyTrade Bot ถูกออกแบบให้เป็นระบบวิจัยและตรวจสอบเชิงปริมาณสำหรับตลาด Polymarket BTC/ETH 5-minute binary markets โดยมีแกนคิด 4 อย่าง:

1. **Paper-first**
   ทุกแนวคิดต้องผ่าน paper runtime และ offline evidence ก่อน

2. **Observability-first**
   ต้องเห็น lifecycle, readiness, cutoff, EV/probability, risk block, liquidity และ replay continuity ก่อนเปลี่ยนพฤติกรรมระบบ

3. **Risk-first**
   เงินทุน การจำกัด exposure, drawdown, reconciliation และ stale-book protection สำคัญกว่าจำนวน entry

4. **Research-grade evolution**
   ค่อย ๆ ไปจาก signal trading → probability diagnostics → offline inventory replay → bounded inventory design โดยไม่ข้ามขั้น

---

## 🧭 Current North Star

```text
single-entry signal trading
  -> regime-aware probability diagnostics
  -> paper-only inventory replay research
  -> bounded multi-price inventory design
  -> continuous probabilistic inventory trading
     only after paper evidence supports it
```

สิ่งสำคัญ: roadmap นี้ **ไม่อนุญาตให้เปลี่ยน execution behavior, risk sizing, strategy threshold หรือ live behavior เอง** จนกว่าจะมี task ที่ scope ชัดเจน

---

## 🧱 System Architecture

```text
+--------------------------------------------------------------+
|                         main.py                              |
|              CLI / mode routing / runtime loop               |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                   polymarket/trader.py                       |
|      market scan / analysis / risk plan / paper execution    |
|      lifecycle visibility / terminal state / JSONL events    |
+--------------+--------------+--------------+-----------------+
               |              |              |
               v              v              v
+-------------------+ +----------------+ +--------------------+
| Market Discovery  | | Signal / EV     | | Risk / Order Guard |
| Gamma / tokens    | | probability     | | RiskPlan           |
| active windows    | | fair value      | | OrderIntent        |
+---------+---------+ +-------+--------+ +---------+----------+
          |                   |                    |
          v                   v                    v
+-------------------+ +----------------+ +--------------------+
| Orderbook / CLOB  | | Observability   | | Paper Runtime      |
| bid / ask / spread| | JSONL / logs    | | simulated receipts |
| freshness checks  | | reports         | | virtual cash/PnL   |
+-------------------+ +----------------+ +--------------------+
```

---

## 🔁 Runtime Flow

```text
Start
  │
  ├─ Load settings / validate config
  │
  ├─ Select mode
  │    ├─ default -> paper
  │    ├─ paper   -> simulated execution only
  │    └─ live    -> readiness preflight required
  │
  ├─ Discover BTC/ETH 5M markets
  │
  ├─ Resolve tokens + orderbooks
  │
  ├─ Analyze timing / liquidity / EV / probability
  │
  ├─ Build risk plan
  │
  ├─ Block or allow paper intent
  │
  ├─ Emit JSONL / CSV / terminal evidence
  │
  └─ Offline tools review generated reports
```

---

## 🧬 Quant Lifecycle Vocabulary

ระบบนี้ใช้ภาษา lifecycle เพื่อแยกช่วงของตลาด 5 นาทีให้ชัดขึ้น:

| Phase | ความหมาย |
|---|---|
| `OPENING_SCAN` | เจอตลาดใหม่ resolve token / warm orderbook / เริ่มเห็น tradable window |
| `ACTIVE_INVENTORY_TRADING` | ช่วงที่อนาคตอาจมี starter / reload / reduce ภายใต้ bounded risk |
| `PROFIT_MANAGEMENT` | ช่วงจัดการกำไร ลด exposure หรือ lock gain |
| `FINAL_DERISK` | ช่วงใกล้ปิดตลาด ต้อง derisk ก่อน hard close |
| `CLOSED_OR_UNSAFE` | ตลาดปิดหรือข้อมูลไม่ปลอดภัย หยุด entry |

ตอนนี้ lifecycle vocabulary เป็นทั้ง runtime visibility และ research vocabulary แต่ **ยังไม่ใช่ใบอนุญาตให้เปลี่ยน strategy หรือ execution**

---

## 🛡️ Safety Philosophy

ระบบนี้ออกแบบโดยถือว่า survival มาก่อน opportunity count

| Guardrail | หลักการ |
|---|---|
| Paper default | `python main.py` ต้องปลอดภัยและเป็น paper |
| No martingale | ไม่เพิ่ม size เพื่อไล่ขาดทุน |
| No unlimited averaging down | ไม่มีการถัวไม่จำกัด |
| Bounded inventory only | future inventory ต้องมี cap, stop, forced exit |
| OrderIntent guard | ENTRY/EXIT ต้องถูกแยกและตรวจสอบ |
| Reconciliation first | unknown state / mismatch ต้อง block entry |
| Stale-book protection | orderbook เก่าหรือไม่ครบห้ามใช้เป็น approval |
| Cutoff discipline | ใกล้ปิดตลาดต้อง conservative |
| Offline evidence only | analyzer/replay ไม่ป้อนกลับ runtime อัตโนมัติ |
| Live mode explicit | live ต้อง explicit และ readiness ต้องผ่าน |

---

## ✅ What Works Now

| Area | Status |
|---|---|
| Paper runtime | ใช้งานเป็น safe default |
| BTC/ETH 5M scanner | มี runtime path |
| CLOB orderbook visibility | เห็น bid/ask/spread ใน evidence ล่าสุด |
| Terminal UI V2 | responsive dashboard |
| JSONL quant logging | มี structured runtime events |
| Offline data quality | มี checker |
| Replay analyzer | มี report generator |
| No-entry analyzer | มี root-cause diagnostics |
| Session runtime evaluator | มี paper health / bottleneck summary |
| Offline Telegram summary | มี explicit sender/formatter |
| Offline report dashboard | มี local read-only dashboard |
| Risk modules | มี RiskPlan, tiers, risk modes |
| Paper/live separation | มี tests และ guardrails |

---

## 🚫 What Is Not Claimed

โปรเจกต์นี้ **ไม่อ้าง** สิ่งต่อไปนี้:

- ❌ ไม่อ้างว่า live-ready
- ❌ ไม่อ้างว่ากำไรจริง
- ❌ ไม่อ้างว่าเป็น production HFT
- ❌ ไม่อ้างว่า fully autonomous success
- ❌ ไม่อ้างว่า execution ผ่านการ validate ครบแล้ว
- ❌ ไม่อ้างว่า replay output เป็น trade approval
- ❌ ไม่อ้างว่า no-entry session คือ failure เสมอ

---

## 📌 Latest Evidence Snapshot

หลักฐาน scoped paper run ล่าสุดที่ใช้เป็น reference:

```text
run_id: 20260515T143223Z_22760_1b6c0b35
continuity: PASS
primary root cause: cutoff / time_unsafe
secondary root cause: risk_plan_zero
execution root cause: NO
orderbook/liquidity: not primary blocker
EV/probability visibility: present in offline admission/no-entry evidence
runtime behavior changed: NO
```

การตีความ:

- ระบบวิเคราะห์ได้ ไม่ใช่หายไปก่อน analyze ทั้งหมด
- orderbook/liquidity ไม่ใช่ blocker หลักใน run นี้
- entry ถูก block ก่อนถึง true execution attempt
- execution-log volume เป็น diagnostic/non-attempt evidence ไม่ใช่ execution failure
- ประเด็นหลักตอนนี้คือ **timing/cutoff pressure** และ **zero-size risk plan**

---

## 🚀 Quick Start

### 1. สร้าง environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. สร้าง `.env`

```bash
copy .env.example .env
```

ก่อน run ทุกครั้ง ตรวจ `.env`:

```text
PAPER_TRADING=true
DRY_RUN=true
```

ถ้าเจอ `PAPER_TRADING=false` หรือ `DRY_RUN=false` ให้ถือว่า repo อยู่ใน live-risk context ทันที

---

## ▶️ How To Run

### Safe default paper runtime

```bash
python main.py
```

### Explicit paper runtime

```bash
python main.py --mode paper --interval 60
```

### Responsive terminal dashboard

```bash
python main.py --mode paper --interval 60 --ui auto --fps medium
```

### Read-only verify

```bash
python main.py --mode verify
```

### Live runtime

```bash
python main.py --mode live --interval 60
```

> ใช้เฉพาะเมื่อมี explicit operator intent และ readiness evidence ครบเท่านั้น
> สถานะปัจจุบันยังไม่ควรเรียกว่า live-ready

---

## 🧪 Offline Evidence Tools

เครื่องมือกลุ่มนี้เป็น **offline-only** อ่าน generated evidence แล้วสร้าง report เท่านั้น ไม่เปลี่ยน runtime decision

| Tool | Purpose | Example |
|---|---|---|
| `quant_data_quality.py` | ตรวจ JSONL integrity / run continuity | `python tools/quant_data_quality.py --date 2026-05-15 --run-id RUN_ID --write-report` |
| `replay_analyzer.py` | สรุป replay จาก quant events | `python tools/replay_analyzer.py --date 2026-05-15 --csv` |
| `no_entry_analyzer.py` | วิเคราะห์ no-entry root cause | `python tools/no_entry_analyzer.py --date 2026-05-15 --run-id RUN_ID --write-report` |
| `session_runtime_evaluator.py` | สรุป health / bottleneck / readiness | `python tools/session_runtime_evaluator.py --date 2026-05-15 --run-id RUN_ID --write-report` |
| `paper_evaluation_report.py` | PASS / CAUTION / FAIL paper evidence | `python tools/paper_evaluation_report.py --date 2026-05-15` |
| `offline_telegram_summary.py` | สรุป report เป็น Telegram-safe message | `python tools/offline_telegram_summary.py --date 2026-05-15 --run-id RUN_ID` |

---

## 📊 Offline Quant Report Dashboard

มี local dashboard แบบ read-only สำหรับดู completed reports ใต้ `runtime/reports/*.json`

```bash
python dashboard/offline_quant_report_dashboard.py --reports-dir runtime/reports --host 127.0.0.1 --port 8765
```

เปิด:

```text
http://127.0.0.1:8765
```

Dashboard แสดง:

| Panel | แสดงอะไร |
|---|---|
| Latest run | run_id ล่าสุดจาก report |
| Continuity | PASS / FAIL / UNKNOWN |
| Root cause | primary / secondary category |
| Block counts | `time_unsafe`, `risk_plan_zero` |
| Lifecycle distribution | phase counts |
| EV visibility | value/null/null-reason coverage |
| Liquidity/orderbook | readiness, stale/empty/unavailable counts |
| Bad JSON warning | malformed JSONL impact |
| Timeline cards | replay / continuity / execution evidence summary |

ข้อจำกัด:

- อ่านเฉพาะ `runtime/reports/*.json`
- ไม่แตะ raw runtime writers
- ไม่เรียก live API
- ไม่มี trading controls
- ไม่เปลี่ยน paper/live behavior

---

## 📬 Telegram Summary

ระบบมี offline Telegram summary tool สำหรับส่งสรุปจาก generated reports แบบ explicit เท่านั้น

Preview:

```bash
python tools/offline_telegram_summary.py --date 2026-05-15 --run-id 20260515T143223Z_22760_1b6c0b35
```

ส่งจริงต้องใส่ `--send`:

```bash
python tools/offline_telegram_summary.py --date 2026-05-15 --run-id 20260515T143223Z_22760_1b6c0b35 --send
```

สำคัญ:

- ไม่ wired เข้า runtime
- ไม่ส่งอัตโนมัติจาก trading loop
- ไม่ใช้เป็น trade approval
- เป็น report-derived evidence summary เท่านั้น

---

## 🧮 Quant Concepts In The System

| Concept | ใช้เพื่อ |
|---|---|
| EV / expected value | วัดความคุ้มค่าหลังราคาและ spread |
| Probability model | ประเมิน true probability / fair value |
| Market regime | volatility / trend / compression context |
| Liquidity state | ตรวจ spread, depth, stale/empty book |
| Cutoff pressure | วัดความเสี่ยงจากเวลาที่เหลือก่อน market close |
| Dynamic risk budget | จำกัด exposure ตาม bankroll, drawdown, tier |
| Risk mode | NORMAL / DEFENSIVE / MICRO_RECOVERY / LOCKDOWN |
| MFE / MAE | future paper replay สำหรับ missed opportunity |
| Inventory lifecycle | future bounded inventory research |
| Reconciliation | ป้องกัน unknown/partial/mismatched position state |

---

## 🧯 Risk Model Principles

```text
capital survival
  > data integrity
  > market readiness
  > liquidity quality
  > timing safety
  > EV visibility
  > risk plan validity
  > execution attempt
```

หากข้อมูลไม่พร้อม, orderbook stale, cutoff pressure สูง, risk plan เป็นศูนย์, หรือ reconciliation ไม่ปลอดภัย ระบบควร block entry ได้โดยไม่ถือว่าเป็น failure เสมอ

---

## 🧭 Roadmap

| Phase | Scope | Runtime Behavior |
|---|---|---|
| Phase 1 | Regime / probability / indicator evidence / observability | ไม่เปลี่ยน execution |
| Phase 2 | Paper-only inventory replay, reload/unload, opportunity decay, MFE/MAE | offline/paper only |
| Phase 3 | Bounded multi-price inventory engine design | ต้องมี cap, stop, forced exit |
| Phase 4 | Continuous probabilistic inventory trading | ทำได้หลัง paper evidence สนับสนุนเท่านั้น |

Future inventory system ต้องมี:

- max inventory cap
- max market/session risk
- stop loss
- forced exit
- no martingale
- no unlimited averaging down
- reconciliation-safe exits

---

## 🤖 Multi-Agent Workflow

โปรเจกต์นี้มี role docs สำหรับ AI/Codex workflow เพื่อคุม scope และลดการแก้ผิดชั้น

```text
MASTER_AGENT_ROUTER.md
  -> choose exactly one PRIMARY role
  -> choose up to three SUPPORTING roles
  -> inspect only relevant files
  -> preserve do-not-touch boundaries
  -> run targeted validation
```

ตัวอย่าง role สำคัญ:

| Role | ใช้เมื่อ |
|---|---|
| `01_PROJECT_MANAGER_AGENT.md` | scope, roadmap, docs, promotion gates |
| `03_RISK_MANAGER_AGENT.md` | sizing, drawdown, exposure, LOCKDOWN |
| `05_MARKET_DATA_AGENT.md` | market discovery, token, orderbook readiness |
| `07_TEST_CI_AGENT.md` | targeted tests / validation |
| `10_BACKTEST_REPLAY_AGENT.md` | replay, lifecycle, MFE/MAE research |
| `11_OBSERVABILITY_INCIDENT_AGENT.md` | JSONL, logs, reports, incident evidence |
| `13_TELEGRAM_ALERT_AGENT.md` | Telegram routing / summary |
| `14_NO_ENTRY_DIAGNOSTICS_AGENT.md` | no-entry root cause |
| `16_PAPER_EVALUATION_AGENT.md` | PASS / CAUTION / FAIL paper evidence |
| `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` | future lifecycle inventory coordination |

Agent docs เป็น guidance เท่านั้น ไม่ใช่ runtime modules และไม่ใช่ permission ให้เปลี่ยน strategy/risk/execution

---

## 🗂️ Project Structure

```text
.
├─ main.py                         # CLI / runtime mode router
├─ config/                         # settings / env validation
├─ polymarket/                     # canonical Polymarket runtime path
│  ├─ trader.py                    # coordinator
│  ├─ client.py                    # CLOB client
│  ├─ gamma_fetcher.py             # market discovery
│  ├─ market_feed.py               # Binance feed
│  ├─ oracle_price_feed.py         # oracle / PTB path
│  ├─ signal.py                    # signal logic
│  ├─ probability_model.py         # probability path
│  ├─ expected_value.py            # EV calculation
│  ├─ order_manager.py             # RiskPlan builder
│  └─ order_intent.py              # ENTRY / EXIT guard
├─ utils/
│  ├─ risk_manager.py              # hard risk policy
│  ├─ display.py                   # Terminal UI V2
│  ├─ logger.py                    # fail-soft logging
│  ├─ quant_event_logger.py        # structured JSONL events
│  └─ telegram_alerts.py           # cooldown / dedup alerts
├─ tools/
│  ├─ quant_data_quality.py        # offline JSONL quality
│  ├─ replay_analyzer.py           # offline replay report
│  ├─ no_entry_analyzer.py         # no-entry diagnostics
│  ├─ session_runtime_evaluator.py # session health / bottleneck
│  ├─ paper_evaluation_report.py   # PASS / CAUTION / FAIL
│  └─ offline_telegram_summary.py  # offline Telegram summary
├─ dashboard/
│  └─ offline_quant_report_dashboard.py
├─ web-dashboard/                  # separate frontend surface
├─ docs/                           # architecture / runbooks / known issues
├─ tests/                          # targeted regression tests
├─ runtime/                        # generated logs / quant data / reports
├─ logs/                           # generated app logs
├─ logs_vps/                       # VPS evidence logs
└─ backtest_results/               # generated backtest outputs
```

---

## 🧪 Testing

Full suite:

```bash
python -m pytest tests/ -q
```

Targeted examples:

```bash
python -m pytest tests/test_paper_mode.py -q
python -m pytest tests/test_execution_risk_controls.py tests/test_risk_modes.py -q
python -m pytest tests/test_quant_data_quality.py tests/test_replay_analyzer.py -q
python -m pytest tests/test_no_entry_analyzer.py tests/test_offline_quant_report_dashboard.py -q
```

Docs-only changes do not require runtime tests, but markdown diffs should still be reviewed.

---

## 🔍 Current Known Limitations

| Limitation | Current truth |
|---|---|
| Live trading | Not validated |
| Live allowance | ยังเป็น blocker ใน evidence ล่าสุด |
| Live fill/cancel/reconcile | ยังไม่ proven end-to-end |
| Runtime timing | อยู่ระหว่าง investigation |
| Current no-entry root cause | cutoff / time_unsafe |
| Secondary blocker | risk_plan_zero |
| Execution root cause | no, for latest scoped evidence |
| Daily Telegram copy | ยังมี stale wording บางส่วน |
| HFT path | experimental / paper-first only |
| Dashboard surfaces | ยัง overlap, ต้อง consolidate ในอนาคต |

---

## 🧾 Operator Checklist

ก่อน paper run:

- [ ] ตรวจ `.env`
- [ ] ยืนยัน `PAPER_TRADING=true`
- [ ] ยืนยัน `DRY_RUN=true`
- [ ] ใช้ `python main.py` หรือ explicit paper command
- [ ] เห็น paper banner
- [ ] เห็น orderbook bid/ask/spread
- [ ] เห็น portfolio source เป็น paper/virtual หรือ wallet-reference paper

หลัง paper run:

- [ ] run data quality
- [ ] run replay analyzer
- [ ] run no-entry analyzer ถ้าไม่มี entry/fill
- [ ] ตรวจ continuity แบบ run-scoped ถ้ามีหลาย run_id
- [ ] เปิด offline dashboard
- [ ] สรุป root cause โดยไม่ loosen risk gate

ก่อนพูดว่า live-ready:

- [ ] allowance ready
- [ ] order placement proven
- [ ] fill detection proven
- [ ] cancel path proven
- [ ] reconciliation proven
- [ ] live wallet balance source verified
- [ ] risk guards still active
- [ ] logs/terminal prove every claim

---

## 📚 Key Docs

| File | Purpose |
|---|---|
| `CODEX_START_HERE.md` | startup context |
| `PROJECT_RULES.md` | safety and scope rules |
| `AGENTS.md` | AI agent operating rules |
| `MASTER_AGENT_ROUTER.md` | role selection |
| `CURRENT_PROJECT_STATUS.md` | latest operational truth |
| `PROJECT_STRUCTURE.md` | architecture pointer |
| `docs/PROJECT_STRUCTURE.md` | canonical structure |
| `docs/KNOWN_ISSUES.md` | active blockers / technical debt |
| `FILE_INDEX.md` | quick file map |
| `QUANT_FUTURE_DECISION_ENGINE.md` | three-option future analysis framework |
| `docs/PAPER_TRADING_RUNBOOK.md` | paper operation workflow |
| `docs/OBSERVABILITY_PLAN.md` | observability roadmap |

---

## 🧠 Design Ethos

> “ระบบที่ไม่เทรด เพราะ risk/cutoff/data ไม่ปลอดภัย อาจเป็นระบบที่กำลังทำงานถูกต้อง”

PolyTrade Bot ไม่ได้ถูกออกแบบให้ยิง entry ให้มากที่สุด แต่ถูกออกแบบให้ถามคำถามที่สำคัญกว่า:

- ตลาดพร้อมจริงไหม?
- orderbook สดพอไหม?
- spread คุ้มไหม?
- probability/EV เห็นจริงไหม?
- cutoff pressure ทำให้ entry unsafe ไหม?
- risk plan มี size ที่ปลอดภัยไหม?
- state ของ position/reconciliation เชื่อถือได้ไหม?
- ถ้าไม่มี trade นั่นคือพลาด opportunity หรือป้องกันทุนถูกต้อง?

คำตอบต้องมาจาก evidence ไม่ใช่ intuition

---

## 🛑 Non-Negotiables

- Paper mode เป็น default
- Offline analyzers เป็น evidence เท่านั้น
- ห้าม bypass risk gates
- ห้าม bypass OrderIntent
- ห้าม bypass reconciliation
- ห้ามใช้ stale orderbook เพื่อ approve trade
- ห้ามเปลี่ยน live flags โดยไม่ตั้งใจ
- ห้ามอ้าง profit หรือ live readiness จาก paper evidence
- ห้าม martingale
- ห้าม unlimited averaging down
- ห้ามแก้ strategy/risk/execution ในงาน docs/observability โดยไม่มี scope ชัดเจน

---

## 🧭 Next Safest Paths

### OPTION 1 — SAFE EV PRESERVATION

รักษา runtime behavior ปัจจุบันไว้และใช้ offline dashboard + no-entry reports เพื่อยืนยันว่า cutoff/time_unsafe ยังเป็น bottleneck หลักจริงหรือไม่ใน paper runs ถัดไป

### OPTION 2 — AGGRESSIVE INFORMATION DISCOVERY

เพิ่ม paper-only/offline diagnostics สำหรับ timing window, lifecycle arrival, EV visibility และ risk_plan_zero distribution โดยไม่ผูกกลับ runtime decision

### OPTION 3 — STRUCTURAL / ROOT-CAUSE PATH

ตรวจ runtime cadence/timing architecture แยกจาก strategy/risk เพื่อหาว่า cutoff pressure เป็น symptom ของ scheduler cadence, market admission timing หรือ lifecycle handoff gap หรือไม่

---

## 🏁 Final Word

PolyTrade Bot คือระบบ quant research ที่กำลังถูกทำให้เห็นความจริงมากขึ้นเรื่อย ๆ ผ่าน paper runtime, structured logs, replay, no-entry diagnostics, dashboards และ safety-first workflow

เป้าหมายไม่ใช่ “เทรดให้ได้ตอนนี้”
เป้าหมายคือ “รู้ให้แน่ชัดว่าควรเทรดหรือไม่ และเพราะอะไร”
