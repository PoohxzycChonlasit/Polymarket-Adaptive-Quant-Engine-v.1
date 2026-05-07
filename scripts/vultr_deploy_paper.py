from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx


VULTR_API = "https://api.vultr.com/v2"


def _git_remote_url() -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _cloud_init(repo_url: str, branch: str, duration_hours: float) -> str:
    return f"""#!/bin/bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git curl ca-certificates python3 python3-venv python3-pip

mkdir -p /opt
if [ ! -d /opt/polytrade/.git ]; then
  git clone --branch "{branch}" "{repo_url}" /opt/polytrade
else
  cd /opt/polytrade
  git fetch origin "{branch}"
  git checkout "{branch}"
  git pull --ff-only origin "{branch}"
fi

cd /opt/polytrade
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi

sed -i 's/^PAPER_TRADING=.*/PAPER_TRADING=true/' .env || true
sed -i 's/^DRY_RUN=.*/DRY_RUN=true/' .env || true

cat >/etc/systemd/system/polytrade-hft-paper.service <<'SERVICE'
[Unit]
Description=PolyTrade HFT Paper Run
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/polytrade
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONIOENCODING=utf-8
ExecStart=/opt/polytrade/.venv/bin/python hft_paper_run.py --duration-hours {duration_hours} --loop-sec 10
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable polytrade-hft-paper.service
systemctl restart polytrade-hft-paper.service
"""


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _request(client: httpx.Client, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    resp = client.request(method, f"{VULTR_API}{path}", **kwargs)
    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}
    if resp.status_code >= 400:
        raise RuntimeError(f"Vultr API {method} {path} failed: HTTP {resp.status_code} {payload}")
    return payload


def deploy(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.getenv("VULTR_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("VULTR_API_KEY is not set.")

    repo_url = args.repo_url or os.getenv("POLYTRADE_REPO_URL", "").strip() or _git_remote_url()
    if not repo_url:
        raise RuntimeError("Repository URL not found. Set POLYTRADE_REPO_URL or pass --repo-url.")

    user_data = base64.b64encode(
        _cloud_init(repo_url=repo_url, branch=args.branch, duration_hours=args.duration_hours).encode("utf-8")
    ).decode("ascii")

    payload: dict[str, Any] = {
        "region": args.region,
        "plan": args.plan,
        "os_id": args.os_id,
        "label": args.label,
        "hostname": args.label,
        "enable_ipv6": False,
        "backups": "disabled",
        "user_data": user_data,
        "activation_email": False,
    }
    ssh_key_id = args.ssh_key_id or os.getenv("VULTR_SSH_KEY_ID", "").strip()
    if ssh_key_id:
        payload["sshkey_id"] = [ssh_key_id]

    with httpx.Client(headers=_headers(api_key), timeout=httpx.Timeout(30.0)) as client:
        created = _request(client, "POST", "/instances", json=payload)
        instance = created["instance"]
        instance_id = instance["id"]

        deadline = time.time() + args.wait_seconds
        while time.time() < deadline:
            current = _request(client, "GET", f"/instances/{instance_id}")["instance"]
            if current.get("main_ip") and current.get("main_ip") != "0.0.0.0":
                instance = current
                break
            time.sleep(5)

    return {
        "instance_id": instance_id,
        "label": instance.get("label"),
        "main_ip": instance.get("main_ip", ""),
        "region": instance.get("region"),
        "plan": instance.get("plan"),
        "repo_url": repo_url,
        "branch": args.branch,
        "duration_hours": args.duration_hours,
        "service": "polytrade-hft-paper.service",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy PolyTrade HFT paper run to a Vultr instance.")
    parser.add_argument("--repo-url", default="", help="Git repo URL the server can clone. Defaults to git origin.")
    parser.add_argument("--branch", default=os.getenv("POLYTRADE_BRANCH", "main"))
    parser.add_argument("--region", default=os.getenv("VULTR_REGION", "sgp"))
    parser.add_argument("--plan", default=os.getenv("VULTR_PLAN", "vc2-1c-1gb"))
    parser.add_argument("--os-id", type=int, default=int(os.getenv("VULTR_OS_ID", "1743")))
    parser.add_argument("--label", default=os.getenv("VULTR_LABEL", "polytrade-hft-paper"))
    parser.add_argument("--ssh-key-id", default="")
    parser.add_argument("--duration-hours", type=float, default=float(os.getenv("HFT_PAPER_DURATION_HOURS", "48")))
    parser.add_argument("--wait-seconds", type=int, default=180)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = deploy(args)
    print(json.dumps(result, indent=2))
    if result.get("main_ip"):
        print()
        print("SSH:")
        print(f"  ssh root@{result['main_ip']}")
        print("Status:")
        print("  systemctl status polytrade-hft-paper.service")
        print("Logs:")
        print("  journalctl -u polytrade-hft-paper.service -f")
        print("Summary after finish:")
        print("  cat /opt/polytrade/runtime/hft_summary_latest.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
