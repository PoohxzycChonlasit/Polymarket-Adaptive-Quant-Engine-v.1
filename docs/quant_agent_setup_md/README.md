# Quant Agent System

เอกสารชุดนี้เป็น operating manual สำหรับจัดงานของ PolyTrade ให้เหมือน quant trading desk ขนาดเล็ก โดยแยกบทบาท agent, workflow, และ template ออกจาก `AGENTS.md` หลักของ Codex

## Start Here

| File | Purpose |
| --- | --- |
| [00_MASTER_CONTEXT.md](00_MASTER_CONTEXT.md) | ภาพรวมเป้าหมาย หลักคิด และกฎที่ห้ามละเมิด |
| [01_QUANT_OPERATING_SYSTEM.md](01_QUANT_OPERATING_SYSTEM.md) | วิธีทำงานรายวันแบบ quant desk |
| [02_AGENT_INDEX.md](02_AGENT_INDEX.md) | รายชื่อ agent และลำดับการใช้งาน |

## Agent Roles

| Phase | Agent | File |
| --- | --- | --- |
| 1 | Project Manager | [roles/01_PROJECT_MANAGER_AGENT.md](roles/01_PROJECT_MANAGER_AGENT.md) |
| 1 | Code Architect | [roles/02_CODE_ARCHITECT_AGENT.md](roles/02_CODE_ARCHITECT_AGENT.md) |
| 1 | Risk Manager | [roles/03_RISK_MANAGER_AGENT.md](roles/03_RISK_MANAGER_AGENT.md) |
| 1 | Exit Execution | [roles/04_EXIT_EXECUTION_AGENT.md](roles/04_EXIT_EXECUTION_AGENT.md) |
| 1 | Market Data | [roles/05_MARKET_DATA_AGENT.md](roles/05_MARKET_DATA_AGENT.md) |
| 1 | Position Reconciliation | [roles/06_POSITION_RECONCILIATION_AGENT.md](roles/06_POSITION_RECONCILIATION_AGENT.md) |
| 1 | Test CI | [roles/07_TEST_CI_AGENT.md](roles/07_TEST_CI_AGENT.md) |
| 2 | Research Quant | [roles/08_RESEARCH_QUANT_AGENT.md](roles/08_RESEARCH_QUANT_AGENT.md) |
| 2 | Signal Strategy | [roles/09_SIGNAL_STRATEGY_AGENT.md](roles/09_SIGNAL_STRATEGY_AGENT.md) |
| 2 | Backtest Replay | [roles/10_BACKTEST_REPLAY_AGENT.md](roles/10_BACKTEST_REPLAY_AGENT.md) |
| 2 | Observability Incident | [roles/11_OBSERVABILITY_INCIDENT_AGENT.md](roles/11_OBSERVABILITY_INCIDENT_AGENT.md) |
| 2 | Review Learning | [roles/12_REVIEW_LEARNING_AGENT.md](roles/12_REVIEW_LEARNING_AGENT.md) |

## Playbooks

| File | Purpose |
| --- | --- |
| [playbooks/CODEX_WORKFLOW.md](playbooks/CODEX_WORKFLOW.md) | วิธีสั่ง Codex ให้ทำงานแบบ scoped และปลอดภัย |
| [playbooks/DAILY_WORKFLOW.md](playbooks/DAILY_WORKFLOW.md) | ขั้นตอนเริ่มงาน/ปิดงานรายวัน |
| [playbooks/INCIDENT_RESPONSE.md](playbooks/INCIDENT_RESPONSE.md) | ขั้นตอนรับมือเหตุผิดปกติ |

## Templates

| File | Purpose |
| --- | --- |
| [templates/AGENT_PROMPT_PACK.md](templates/AGENT_PROMPT_PACK.md) | prompt pack สำหรับเรียก agent |
| [templates/BUGS_AND_FIXES_TEMPLATE.md](templates/BUGS_AND_FIXES_TEMPLATE.md) | template บันทึกบั๊กและการแก้ |
| [templates/CURRENT_STATUS_TEMPLATE.md](templates/CURRENT_STATUS_TEMPLATE.md) | template สรุปสถานะปัจจุบัน |
| [templates/TRADE_REVIEW_TEMPLATE.md](templates/TRADE_REVIEW_TEMPLATE.md) | template review trade |

## Usage Rule

ใช้เอกสารนี้เป็นคู่มือวางแผนและ review งาน ส่วนกฎที่ Codex ต้อง auto-load ทุก session ยังอยู่ที่ [../../AGENTS.md](../../AGENTS.md)
