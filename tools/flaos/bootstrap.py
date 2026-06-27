"""
FLAOS Bootstrap Context Resolver.

Read-only tool: loads operational JSON files and produces a compact
ExecutionSnapshot for the next task. No file writes, no state mutation,
no git commits, no trading runtime dependency.

Usage:
    python tools/flaos/bootstrap.py
    python tools/flaos/bootstrap.py --json     # compact JSON (default)
    python tools/flaos/bootstrap.py --pretty   # pretty-printed JSON
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "state": ROOT / "docs/operations/ACTIVE_WORKFLOW_STATE_001.json",
    "queue": ROOT / "docs/operations/TASK_QUEUE_001.json",
    "agent_pipeline": ROOT / "docs/operations/AGENT_PIPELINE_001.json",
    "tool_pipeline": ROOT / "docs/operations/TOOL_PIPELINES_001.json",
    "skill_registry": ROOT / "docs/operations/skills/SKILL_REGISTRY_001.json",
    "loop_memory": ROOT / "docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json",
}

# High-risk trigger keywords — any task scope containing these routes to HIGH_RISK_STOP_WORKFLOW
HIGH_RISK_TRIGGERS = {
    "execution", "live_trading", "live order", "place_order", "wallet",
    "bankroll", "reconciliation", "deploy", "runtime data deletion",
    "risk_plan", "sizing", "allowance",
}

# Auto-prepend triggers for quant_safety_review
QUANT_SAFETY_PREPEND_TRIGGERS = {
    "python_files_in_scope", "trading_logic_in_scope", "risk_or_sizing_in_scope",
    "execution_path_in_scope", "wallet_or_bankroll_in_scope", "live_trading_keyword",
    "runtime_data_deletion",
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load(key: str) -> dict | list:
    path = FILES[key]
    if not path.exists():
        print(f"ERROR: required file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def _load_all() -> dict:
    return {k: _load(k) for k in FILES}


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

def _next_task_entry(queue_data: dict, next_task_id: str) -> dict | None:
    for entry in queue_data.get("queue", []):
        if entry.get("task_id") == next_task_id:
            return entry
    return None


def _select_agent_pipeline(pipeline_data: dict, task_class: int, workflow_tier: str) -> dict | None:
    """Select the most specific pipeline for this task_class + workflow_tier.

    Specificity score (higher = preferred):
    - Primary tier match (tier is first in workflow_tiers list): +10
    - Pipeline ID contains tier name: +5
    - Fewer task_classes (more targeted): +len(all_task_classes) - len(this_pipeline_task_classes)
    - Risk level for risk-appropriate matching: GATE->MEDIUM preferred over NONE
    """
    candidates = [
        p for p in pipeline_data.get("pipelines", [])
        if task_class in p.get("task_classes", []) and workflow_tier in p.get("workflow_tiers", [])
    ]
    if not candidates:
        return None

    risk_for_tier = {"GATE": "MEDIUM", "STANDARD": "MEDIUM", "LOOP": "LOW", "FAST": "NONE"}
    preferred_risk = risk_for_tier.get(workflow_tier, "NONE")
    risk_order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "CRITICAL": 3}
    all_task_classes: set[int] = set()
    for p in candidates:
        all_task_classes.update(p.get("task_classes", []))

    def score(p: dict) -> int:
        s = 0
        tiers = p.get("workflow_tiers", [])
        if tiers and tiers[0] == workflow_tier:
            s += 10
        if workflow_tier in (p.get("pipeline_id", "")):
            s += 5
        s += len(all_task_classes) - len(p.get("task_classes", []))
        # Prefer risk level appropriate to the tier
        r = p.get("risk_level", "NONE")
        if r == preferred_risk:
            s += 3
        return s

    return max(candidates, key=score)


def _select_tool_pipeline(pipeline_data: dict, pipeline_id: str) -> dict | None:
    for p in pipeline_data.get("pipelines", []):
        if p.get("pipeline_id") == pipeline_id:
            return p
    return None


def _select_skills(skill_data: dict, task_class: int, workflow_tier: str,
                    agent_pipeline_id: str) -> list[dict]:
    skills: list[dict] = []
    registry = skill_data.get("skills", [])

    # Determine if quant_safety_review should auto-prepend
    # For GATE tier tasks (task_class=2 targeting trader.py) — yes
    needs_quant_safety = task_class in (2, 6, 7, 8) or workflow_tier == "GATE"

    if needs_quant_safety:
        for s in registry:
            if s.get("skill_id") == "quant_safety_review":
                skills.append(s)
                break

    # Select primary skill matching the pipeline
    pipeline_to_skill = {
        "GATE_WORKFLOW": "gate_check",
        "LOW_RISK_REFACTOR_LOOP": "low_risk_refactor",
        "RUNTIME_VALIDATION_LOOP": "runtime_validation",
        "DOCS_LOOP": "docs_housekeeping",
        "REPOSITORY_INTELLIGENCE_LOOP": "repository_audit",
        "HEALTH_CHECK_LOOP": "forbidden_scope_check",
        "TOOL_PIPELINE_LOOP": "forbidden_scope_check",
        "COGNITION_MEMORY_LOOP": "quant_safety_review",
        "HIGH_RISK_STOP_WORKFLOW": "quant_safety_review",
    }
    target_skill_id = pipeline_to_skill.get(agent_pipeline_id)
    if target_skill_id and target_skill_id != "quant_safety_review":
        for s in registry:
            if s.get("skill_id") == target_skill_id:
                if not any(x.get("skill_id") == s.get("skill_id") for x in skills):
                    skills.append(s)
                break

    return skills


def _merge_required_tools(skills: list[dict], tool_pipeline: dict | None) -> list[str]:
    tool_set: list[str] = []
    seen: set[str] = set()

    # From skills
    for skill in skills:
        for t in skill.get("required_tools", []):
            if t not in seen:
                seen.add(t)
                tool_set.append(t)

    # From tool pipeline (add any not already included)
    if tool_pipeline:
        for t in tool_pipeline.get("ordered_tool_sequence", []):
            if t not in seen:
                seen.add(t)
                tool_set.append(t)

    return tool_set


def _merge_memory_reads(skills: list[dict]) -> list[str]:
    seen: set[str] = set()
    reads: list[str] = []
    for s in skills:
        for m in s.get("required_memory_reads", []):
            if m not in seen:
                seen.add(m)
                reads.append(m)
    return reads


def _merge_stop_conditions(skills: list[dict], agent_pipeline: dict | None,
                            tool_pipeline: dict | None) -> list[str]:
    seen: set[str] = set()
    stops: list[str] = []
    sources = [
        *(s.get("stop_conditions", []) for s in skills),
        (agent_pipeline or {}).get("stop_conditions", []),
        (tool_pipeline or {}).get("stop_conditions", []),
    ]
    for source in sources:
        for s in source:
            if s not in seen:
                seen.add(s)
                stops.append(s)
    return stops


def _best_evidence(skills: list[dict], tool_pipeline: dict | None) -> str:
    grade_order = {"D": 0, "C": 1, "B": 2, "A": 3}
    best = "D"
    for s in skills:
        g = s.get("evidence_required", "D")
        if grade_order.get(g, 0) > grade_order.get(best, 0):
            best = g
    if tool_pipeline:
        g = tool_pipeline.get("required_evidence", "D")
        if grade_order.get(g, 0) > grade_order.get(best, 0):
            best = g
    return best


def _full_accept_allowed(skills: list[dict]) -> bool:
    for s in skills:
        if not s.get("full_accept_allowed", True):
            return False
    return True


# ---------------------------------------------------------------------------
# Last loop memory entry
# ---------------------------------------------------------------------------

def _last_loop_entry(memory_data: list) -> dict | None:
    if isinstance(memory_data, list) and memory_data:
        return memory_data[-1]
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_snapshot(pretty: bool = False) -> int:
    data = _load_all()

    state = data["state"]
    queue = data["queue"]
    agent_pipeline_data = data["agent_pipeline"]
    tool_pipeline_data = data["tool_pipeline"]
    skill_data = data["skill_registry"]
    memory_data = data["loop_memory"]

    # Resolve next task
    next_task_id: str = state.get("next_task", "UNKNOWN")
    workflow_tier: str = state.get("next_workflow_tier", "LOOP")
    blocked: bool = bool(state.get("blocked", False))

    if blocked:
        print(json.dumps({
            "error": "BLOCKED",
            "reason": state.get("notes", "See ACTIVE_WORKFLOW_STATE_001.json for block reason"),
            "next_task": next_task_id,
        }, indent=2 if pretty else None))
        return 1

    # Find task queue entry
    task_entry = _next_task_entry(queue, next_task_id)
    task_class: int = task_entry.get("task_class", 3) if task_entry else 3
    allowed_scope: list[str] = task_entry.get("allowed_scope", []) if task_entry else []

    # Select agent pipeline
    agent_pipeline = _select_agent_pipeline(agent_pipeline_data, task_class, workflow_tier)
    agent_pipeline_id = (agent_pipeline or {}).get("pipeline_id", "UNKNOWN")

    # Select tool pipeline matching agent pipeline id
    tool_pipeline = _select_tool_pipeline(tool_pipeline_data, agent_pipeline_id)

    # Select skills
    skills = _select_skills(skill_data, task_class, workflow_tier, agent_pipeline_id)

    # Merge required tools, memory reads, stop conditions
    required_tools = _merge_required_tools(skills, tool_pipeline)
    required_memory_reads = _merge_memory_reads(skills)
    stop_conditions = _merge_stop_conditions(skills, agent_pipeline, tool_pipeline)
    required_evidence = _best_evidence(skills, tool_pipeline)
    full_accept = _full_accept_allowed(skills)

    # Last loop result
    last_entry = _last_loop_entry(memory_data)
    last_result = last_entry.get("result", "UNKNOWN") if last_entry else "UNKNOWN"
    last_loop_id = last_entry.get("loop_id", "UNKNOWN") if last_entry else "UNKNOWN"

    snapshot = {
        "task_id": next_task_id,
        "task_class": task_class,
        "workflow_tier": workflow_tier,
        "agent_pipeline_id": agent_pipeline_id,
        "role_sequence": (agent_pipeline or {}).get("role_sequence", []),
        "tool_pipeline_id": (tool_pipeline or {}).get("pipeline_id", "UNKNOWN"),
        "skills": [s.get("skill_id") for s in skills],
        "required_tools": required_tools,
        "required_memory_reads": required_memory_reads,
        "required_evidence": required_evidence,
        "max_repairs": (tool_pipeline or {}).get("max_repairs", 0),
        "full_accept_allowed": full_accept,
        "stop_conditions": stop_conditions,
        "commit_policy": (tool_pipeline or {}).get("commit_policy", "TYPE_C_ONLY"),
        "allowed_scope": allowed_scope,
        "final_output_format": "docs/reports/{task_id}.md + loop_memory entry",
        "last_loop_id": last_loop_id,
        "last_loop_result": last_result,
        "current_phase": state.get("current_phase", ""),
        "source_files_loaded": [str(p.relative_to(ROOT)) for p in FILES.values()],
    }

    indent = 2 if pretty else None
    print(json.dumps(snapshot, indent=indent))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FLAOS Bootstrap Context Resolver")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--json", action="store_true", help="Compact JSON output (default)")
    args = parser.parse_args()
    sys.exit(build_snapshot(pretty=args.pretty))


if __name__ == "__main__":
    main()
