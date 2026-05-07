# Vultr Paper Run

Use this when the bot must keep running after the local PC is off. A local process stops when Windows shuts down; a Vultr instance keeps running independently.

## 1. Prepare

Set these environment variables locally:

```powershell
$env:VULTR_API_KEY="..."
$env:POLYTRADE_REPO_URL="https://github.com/PoohxzycChonlasit/polytrade-crypto-scalper-main3.6.git"
$env:POLYTRADE_BRANCH="main"
$env:HFT_PAPER_DURATION_HOURS="48"
```

Optional:

```powershell
$env:VULTR_REGION="sgp"
$env:VULTR_PLAN="vc2-1c-1gb"
$env:VULTR_OS_ID="1743"
$env:VULTR_SSH_KEY_ID="..."
```

## 2. Deploy

```powershell
python scripts/vultr_deploy_paper.py
```

The script creates a Vultr instance, installs dependencies, starts:

```bash
systemctl start polytrade-hft-paper.service
```

The service runs:

```bash
python hft_paper_run.py --duration-hours 48 --loop-sec 10
```

It stays in paper mode and writes summary files when finished.

## 3. Monitor

SSH to the printed IP:

```bash
ssh root@SERVER_IP
```

Watch logs:

```bash
journalctl -u polytrade-hft-paper.service -f
```

Check service:

```bash
systemctl status polytrade-hft-paper.service
```

Read final summary:

```bash
cat /opt/polytrade/runtime/hft_summary_latest.md
```

Manual summary rerun:

```bash
cd /opt/polytrade
.venv/bin/python scripts/hft_paper_summary.py
```

## 4. Stop

```bash
systemctl stop polytrade-hft-paper.service
```

Delete the Vultr instance from the Vultr panel or API when done to stop billing.
