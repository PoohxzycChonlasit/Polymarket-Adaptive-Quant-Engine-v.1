"""
FLAOS Bootstrap Context Resolver.

Read-only tool: loads operational JSON files and produces a compact
ExecutionSnapshot for the next task. No file writes, no state mutation,
no git commits, no trading runtime dependency.

Usage:
    python tools/flaos/bootstrap.py
    python tools/flaos/bootstrap.py --json     # compact JSON (default)
    python tools/flaos/bootstrap.py --pretty   # pretty-printed JSON
    python tools/flaos/bootstrap.py --diagnose # health checks and exit status
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
    "tool_registry": ROOT / "docs/operations/TOOL_REGISTRY_001.json",
    "skill_registry": ROOT / "docs/operations/skills/SKILL_REGISTRY_001.json",
    "loop_memory": ROOT / "docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json",
}

# Memory OS V2 paths (optional — degrade gracefully if missing)
MEMORY_INDEX_PATH = ROOT / "docs/operations/memory/MEMORY_INDEX_001.json"
SAFETY_MEMORY_PATH = ROOT / "docs/operations/memory/safety/SAFETY_MEMORY.jsonl"

# Task classes / tiers requiring safety memory
SAFETY_MEMORY_REQUIRED_TASK_CLASSES = {4, 6, 7, 8}
SAFETY_MEMORY_REQUIRED_TIERS = {"GATE", "STANDARD"}

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
# Fail-Safe Stop
# ---------------------------------------------------------------------------

def _fail_safe_stop(error_type: str, message: str, missing_or_invalid_file: str = "") -> None:
    """Print the required STOP JSON and exit non-zero."""
    stop_json = {
        "status": "STOP_AND_ESCALATE",
        "error_type": error_type,
        "message": message,
        "missing_or_invalid_file": missing_or_invalid_file,
        "safe_to_continue": False,
        "allowed_repair_scope": [
            "docs/operations/*.json",
            "docs/operations/skills/*.json",
            "docs/reports/*"
        ],
        "recommended_repair_task": "FLAOS_BOOTSTRAP_REPAIR_001",
        "forbidden_actions": [
            "do_not_execute_task",
            "do_not_modify_runtime_code",
            "do_not_commit_runtime",
            "do_not_run_live_trading"
        ]
    }
    print(json.dumps(stop_json, indent=2))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_file_or_fail(key: str) -> dict | list:
    path = FILES[key]
    if not path.exists():
        _fail_safe_stop(
            error_type="MISSING_REQUIRED_FILE",
            message=f"Required file does not exist: {path.name}",
            missing_or_invalid_file=path.name
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message=f"Required file contains invalid JSON: {path.name} ({exc})",
            missing_or_invalid_file=path.name
        )


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_workflow_state(d: dict) -> None:
    if not isinstance(d, dict):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="ACTIVE_WORKFLOW_STATE must be a JSON object",
            missing_or_invalid_file="ACTIVE_WORKFLOW_STATE_001.json"
        )
    required = ["next_task", "next_workflow_tier"]
    for r in required:
        if r not in d:
            _fail_safe_stop(
                error_type="INVALID_JSON_FORMAT",
                message=f"ACTIVE_WORKFLOW_STATE is missing required field: {r}",
                missing_or_invalid_file="ACTIVE_WORKFLOW_STATE_001.json"
            )

def validate_task_queue(d: dict) -> None:
    if not isinstance(d, dict):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="TASK_QUEUE must be a JSON object",
            missing_or_invalid_file="TASK_QUEUE_001.json"
        )
    if "queue" not in d or not isinstance(d["queue"], list):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="TASK_QUEUE is missing 'queue' array",
            missing_or_invalid_file="TASK_QUEUE_001.json"
        )
    required = ["task_id", "workflow_tier", "task_class"]
    for idx, entry in enumerate(d["queue"]):
        if not isinstance(entry, dict):
            _fail_safe_stop(
                error_type="INVALID_JSON_FORMAT",
                message=f"TASK_QUEUE entry at index {idx} must be a JSON object",
                missing_or_invalid_file="TASK_QUEUE_001.json"
            )
        for r in required:
            if r not in entry:
                _fail_safe_stop(
                    error_type="INVALID_JSON_FORMAT",
                    message=f"TASK_QUEUE entry at index {idx} is missing required field: {r}",
                    missing_or_invalid_file="TASK_QUEUE_001.json"
                )

def validate_agent_pipelines(d: dict) -> None:
    if not isinstance(d, dict):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="AGENT_PIPELINE must be a JSON object",
            missing_or_invalid_file="AGENT_PIPELINE_001.json"
        )
    if "pipelines" not in d or not isinstance(d["pipelines"], list):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="AGENT_PIPELINE is missing 'pipelines' array",
            missing_or_invalid_file="AGENT_PIPELINE_001.json"
        )
    required = ["pipeline_id", "task_classes", "workflow_tiers"]
    for idx, p in enumerate(d["pipelines"]):
        if not isinstance(p, dict):
            _fail_safe_stop(
                error_type="INVALID_JSON_FORMAT",
                message=f"AGENT_PIPELINE pipeline entry at index {idx} must be a JSON object",
                missing_or_invalid_file="AGENT_PIPELINE_001.json"
            )
        for r in required:
            if r not in p:
                _fail_safe_stop(
                    error_type="INVALID_JSON_FORMAT",
                    message=f"AGENT_PIPELINE entry at index {idx} is missing required field: {r}",
                    missing_or_invalid_file="AGENT_PIPELINE_001.json"
                )

def validate_tool_pipelines(d: dict) -> None:
    if not isinstance(d, dict):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="TOOL_PIPELINES must be a JSON object",
            missing_or_invalid_file="TOOL_PIPELINES_001.json"
        )
    if "pipelines" not in d or not isinstance(d["pipelines"], list):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="TOOL_PIPELINES is missing 'pipelines' array",
            missing_or_invalid_file="TOOL_PIPELINES_001.json"
        )
    required = ["pipeline_id", "ordered_tool_sequence"]
    for idx, p in enumerate(d["pipelines"]):
        if not isinstance(p, dict):
            _fail_safe_stop(
                error_type="INVALID_JSON_FORMAT",
                message=f"TOOL_PIPELINES pipeline entry at index {idx} must be a JSON object",
                missing_or_invalid_file="TOOL_PIPELINES_001.json"
            )
        for r in required:
            if r not in p:
                _fail_safe_stop(
                    error_type="INVALID_JSON_FORMAT",
                    message=f"TOOL_PIPELINES entry at index {idx} is missing required field: {r}",
                    missing_or_invalid_file="TOOL_PIPELINES_001.json"
                )

def validate_skill_registry(d: dict) -> None:
    if not isinstance(d, dict):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="SKILL_REGISTRY must be a JSON object",
            missing_or_invalid_file="SKILL_REGISTRY_001.json"
        )
    if "skills" not in d or not isinstance(d["skills"], list):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="SKILL_REGISTRY is missing 'skills' array",
            missing_or_invalid_file="SKILL_REGISTRY_001.json"
        )
    required = ["skill_id", "required_tools", "required_memory_reads"]
    for idx, s in enumerate(d["skills"]):
        if not isinstance(s, dict):
            _fail_safe_stop(
                error_type="INVALID_JSON_FORMAT",
                message=f"SKILL_REGISTRY skill entry at index {idx} must be a JSON object",
                missing_or_invalid_file="SKILL_REGISTRY_001.json"
            )
        for r in required:
            if r not in s:
                _fail_safe_stop(
                    error_type="INVALID_JSON_FORMAT",
                    message=f"SKILL_REGISTRY entry at index {idx} is missing required field: {r}",
                    missing_or_invalid_file="SKILL_REGISTRY_001.json"
                )

def validate_tool_registry(d: dict) -> None:
    if not isinstance(d, dict):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="TOOL_REGISTRY must be a JSON object",
            missing_or_invalid_file="TOOL_REGISTRY_001.json"
        )
    if "tools" not in d or not isinstance(d["tools"], list):
        _fail_safe_stop(
            error_type="INVALID_JSON_FORMAT",
            message="TOOL_REGISTRY is missing 'tools' array",
            missing_or_invalid_file="TOOL_REGISTRY_001.json"
        )
    required = ["tool_id"]
    for idx, t in enumerate(d["tools"]):
        if not isinstance(t, dict):
            _fail_safe_stop(
                error_type="INVALID_JSON_FORMAT",
                message=f"TOOL_REGISTRY tool entry at index {idx} must be a JSON object",
                missing_or_invalid_file="TOOL_REGISTRY_001.json"
            )
        for r in required:
            if r not in t:
                _fail_safe_stop(
                    error_type="INVALID_JSON_FORMAT",
                    message=f"TOOL_REGISTRY entry at index {idx} is missing required field: {r}",
                    missing_or_invalid_file="TOOL_REGISTRY_001.json"
                )


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

def _next_task_entry(queue_data: dict, next_task_id: str) -> dict | None:
    for entry in queue_data.get("queue", []):
        if entry.get("task_id") == next_task_id:
            return entry
    return None


def _select_agent_pipeline(pipeline_data: dict, task_class: int, workflow_tier: str) -> dict | None:
    candidates = [
        p for p in pipeline_data.get("pipelines", [])
        if task_class in p.get("task_classes", []) and workflow_tier in p.get("workflow_tiers", [])
    ]
    if not candidates:
        return None

    risk_for_tier = {"GATE": "MEDIUM", "STANDARD": "MEDIUM", "LOOP": "LOW", "FAST": "NONE"}
    preferred_risk = risk_for_tier.get(workflow_tier, "NONE")
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

    needs_quant_safety = task_class in (2, 6, 7, 8) or workflow_tier == "GATE"

    if needs_quant_safety:
        for s in registry:
            if s.get("skill_id") == "quant_safety_review":
                skills.append(s)
                break

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

    for skill in skills:
        for t in skill.get("required_tools", []):
            if t not in seen:
                seen.add(t)
                tool_set.append(t)

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


def _last_loop_entry(memory_data: list) -> dict | None:
    if isinstance(memory_data, list) and memory_data:
        return memory_data[-1]
    return None


# ---------------------------------------------------------------------------
# Memory OS V2 — safety memory loader
# ---------------------------------------------------------------------------

def _load_safety_memory() -> tuple[bool, bool, list[str], str]:
    """Load MEMORY_INDEX and SAFETY_MEMORY.jsonl.

    Returns (index_loaded, safety_loaded, safety_ids, status).
    status: "LOADED" | "DEGRADED" | "STOP_REQUIRED"
    """
    index_loaded = False
    safety_loaded = False
    safety_ids: list[str] = []

    # Load Memory Index (optional — degrade if missing)
    if MEMORY_INDEX_PATH.exists():
        try:
            idx = json.loads(MEMORY_INDEX_PATH.read_text(encoding="utf-8"))
            if isinstance(idx, dict):
                index_loaded = True
        except (json.JSONDecodeError, IOError):
            pass

    # Load Safety Memory JSONL
    if SAFETY_MEMORY_PATH.exists():
        try:
            for line in SAFETY_MEMORY_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                mid = rec.get("memory_id", "")
                if mid:
                    safety_ids.append(mid)
            safety_loaded = True
        except (json.JSONDecodeError, IOError):
            safety_loaded = False

    if safety_loaded and safety_ids:
        status = "LOADED"
    else:
        # File missing or invalid — caller decides DEGRADED vs STOP based on safety_required
        status = "MISSING_OR_INVALID"

    return index_loaded, safety_loaded, safety_ids, status


# ---------------------------------------------------------------------------
# Main snapshot resolver
# ---------------------------------------------------------------------------

def build_snapshot(pretty: bool = False, diagnose: bool = False) -> int:
    # 1. Load and validate state
    state = _load_file_or_fail("state")
    validate_workflow_state(state)

    # 2. Load and validate task queue
    queue = _load_file_or_fail("queue")
    validate_task_queue(queue)

    # Resolve next task ID and workflow tier
    next_task_id: str = state.get("next_task", "UNKNOWN")
    workflow_tier: str = state.get("next_workflow_tier", "LOOP")
    blocked: bool = bool(state.get("blocked", False))

    if blocked:
        if diagnose:
            pass
        else:
            print(json.dumps({
                "error": "BLOCKED",
                "reason": state.get("notes", "See ACTIVE_WORKFLOW_STATE_001.json for block reason"),
                "next_task": next_task_id,
            }, indent=2 if pretty else None))
            return 1

    # Find task queue entry
    task_entry = _next_task_entry(queue, next_task_id)
    if not task_entry:
        _fail_safe_stop(
            error_type="INCONSISTENT_STATE_QUEUE_REFERENCE",
            message=f"next_task '{next_task_id}' not found in TASK_QUEUE",
            missing_or_invalid_file="TASK_QUEUE_001.json"
        )
    task_class: int = task_entry.get("task_class", 3)
    allowed_scope: list[str] = task_entry.get("allowed_scope", [])

    # 3. Load and validate other pipelines and registries
    agent_pipeline_data = _load_file_or_fail("agent_pipeline")
    validate_agent_pipelines(agent_pipeline_data)

    tool_pipeline_data = _load_file_or_fail("tool_pipeline")
    validate_tool_pipelines(tool_pipeline_data)

    tool_registry_data = _load_file_or_fail("tool_registry")
    validate_tool_registry(tool_registry_data)

    skill_data = _load_file_or_fail("skill_registry")
    validate_skill_registry(skill_data)

    # 4. Load loop memory safely (semi-critical)
    loop_memory_path = FILES["loop_memory"]
    loop_memory_exists = loop_memory_path.exists()
    loop_memory_valid = True
    loop_memory_content = []

    if loop_memory_exists:
        try:
            loop_memory_content = json.loads(loop_memory_path.read_text(encoding="utf-8"))
            if not isinstance(loop_memory_content, list):
                loop_memory_valid = False
                loop_memory_content = []
        except json.JSONDecodeError:
            loop_memory_valid = False
            loop_memory_content = []
    else:
        loop_memory_valid = False

    is_write_task = task_class in (4, 6, 7, 8)
    if not loop_memory_valid and is_write_task:
        _fail_safe_stop(
            error_type="MISSING_LOOP_MEMORY_FOR_WRITE_TASK",
            message=f"Loop memory file is missing or invalid, required for write task '{next_task_id}' (class {task_class})",
            missing_or_invalid_file=loop_memory_path.name
        )

    # 4.5 Load Memory OS V2 safety memory
    index_loaded, safety_loaded, safety_ids, safety_status = _load_safety_memory()
    safety_required = (
        task_class in SAFETY_MEMORY_REQUIRED_TASK_CLASSES
        or workflow_tier in SAFETY_MEMORY_REQUIRED_TIERS
    )
    # Resolve final status: LOADED | DEGRADED | STOP_REQUIRED
    if safety_status == "LOADED":
        final_safety_status = "LOADED"
    elif safety_required:
        final_safety_status = "STOP_REQUIRED"
        _fail_safe_stop(
            error_type="SAFETY_MEMORY_REQUIRED_BUT_INVALID",
            message=(
                f"Safety memory is required for task_class={task_class} / tier='{workflow_tier}' "
                f"but SAFETY_MEMORY.jsonl is missing or invalid."
            ),
            missing_or_invalid_file="docs/operations/memory/safety/SAFETY_MEMORY.jsonl"
        )
    else:
        final_safety_status = "DEGRADED"
    safety_status = final_safety_status

    # 5. Resolve pipelines
    agent_pipeline = _select_agent_pipeline(agent_pipeline_data, task_class, workflow_tier)
    if not agent_pipeline or not agent_pipeline.get("pipeline_id") or agent_pipeline.get("pipeline_id") == "UNKNOWN":
        _fail_safe_stop(
            error_type="PIPELINE_NOT_FOUND",
            message=f"No matching agent pipeline found for task_class={task_class} and workflow_tier='{workflow_tier}'",
            missing_or_invalid_file="AGENT_PIPELINE_001.json"
        )
    agent_pipeline_id = agent_pipeline["pipeline_id"]

    tool_pipeline = _select_tool_pipeline(tool_pipeline_data, agent_pipeline_id)
    if not tool_pipeline or not tool_pipeline.get("pipeline_id") or tool_pipeline.get("pipeline_id") == "UNKNOWN":
        _fail_safe_stop(
            error_type="PIPELINE_NOT_FOUND",
            message=f"No matching tool pipeline found for agent_pipeline_id='{agent_pipeline_id}'",
            missing_or_invalid_file="TOOL_PIPELINES_001.json"
        )

    # 6. Resolve skills
    skills = _select_skills(skill_data, task_class, workflow_tier, agent_pipeline_id)
    registered_skills = {s.get("skill_id") for s in skill_data.get("skills", [])}
    for s in skills:
        skill_id = s.get("skill_id")
        if not skill_id or skill_id not in registered_skills:
            _fail_safe_stop(
                error_type="SKILL_NOT_FOUND",
                message=f"Resolved skill '{skill_id}' is missing from SKILL_REGISTRY",
                missing_or_invalid_file="SKILL_REGISTRY_001.json"
            )

    # 7. Merge and validate required tools
    required_tools = _merge_required_tools(skills, tool_pipeline)
    registered_tools = {t.get("tool_id") for t in tool_registry_data.get("tools", [])}
    for tool_id in required_tools:
        if tool_id not in registered_tools:
            _fail_safe_stop(
                error_type="REQUIRED_TOOL_NOT_REGISTERED",
                message=f"Required tool '{tool_id}' is not registered in TOOL_REGISTRY",
                missing_or_invalid_file="TOOL_REGISTRY_001.json"
            )

    # 8. Merge other properties
    required_memory_reads = _merge_memory_reads(skills)
    stop_conditions = _merge_stop_conditions(skills, agent_pipeline, tool_pipeline)
    required_evidence = _best_evidence(skills, tool_pipeline)
    full_accept = _full_accept_allowed(skills)

    # 9. Handle last loop memory
    last_loop_id = "UNKNOWN"
    last_result = "UNKNOWN"
    if loop_memory_valid and loop_memory_content:
        last_entry = _last_loop_entry(loop_memory_content)
        if last_entry:
            last_loop_id = last_entry.get("loop_id", "UNKNOWN")
            last_result = last_entry.get("result", "UNKNOWN")

    # 10. Output formatting
    if diagnose:
        status = "HEALTHY" if loop_memory_valid else "DEGRADED"
        health_report = {
            "status": status,
            "diagnose": {
                "files_exist": {
                    "state": FILES["state"].exists(),
                    "queue": FILES["queue"].exists(),
                    "agent_pipeline": FILES["agent_pipeline"].exists(),
                    "tool_pipeline": FILES["tool_pipeline"].exists(),
                    "tool_registry": FILES["tool_registry"].exists(),
                    "skill_registry": FILES["skill_registry"].exists(),
                    "loop_memory": loop_memory_exists
                },
                "json_parse": {
                    "state": "OK",
                    "queue": "OK",
                    "agent_pipeline": "OK",
                    "tool_pipeline": "OK",
                    "tool_registry": "OK",
                    "skill_registry": "OK",
                    "loop_memory": "OK" if loop_memory_valid else ("MISSING" if not loop_memory_exists else "INVALID")
                },
                "next_task_in_queue": True,
                "agent_pipeline_resolved": True,
                "tool_pipeline_resolved": True,
                "skills_valid": True,
                "tools_registered": True,
                "loop_memory_status": "OK" if loop_memory_valid else "DEGRADED",
                "memory_os_v2": {
                    "memory_index_loaded": index_loaded,
                    "safety_memory_loaded": safety_loaded,
                    "safety_memory_count": len(safety_ids),
                    "safety_memory_status": safety_status,
                    "safety_memory_required": safety_required,
                }
            }
        }
        print(json.dumps(health_report, indent=2 if pretty else None))
        return 0

    snapshot = {
        "task_id": next_task_id,
        "task_class": task_class,
        "workflow_tier": workflow_tier,
        "agent_pipeline_id": agent_pipeline_id,
        "role_sequence": agent_pipeline.get("role_sequence", []),
        "tool_pipeline_id": tool_pipeline.get("pipeline_id", "UNKNOWN"),
        "skills": [s.get("skill_id") for s in skills],
        "required_tools": required_tools,
        "required_memory_reads": required_memory_reads,
        "required_evidence": required_evidence,
        "max_repairs": tool_pipeline.get("max_repairs", 0),
        "full_accept_allowed": full_accept,
        "stop_conditions": stop_conditions,
        "commit_policy": tool_pipeline.get("commit_policy", "TYPE_C_ONLY"),
        "allowed_scope": allowed_scope,
        "final_output_format": "docs/reports/{task_id}.md + loop_memory entry",
        "last_loop_id": last_loop_id,
        "last_loop_result": last_result,
        "current_phase": state.get("current_phase", ""),
        "source_files_loaded": [str(p.relative_to(ROOT)).replace('\\', '/') for p in FILES.values()],
        "memory_os_v2_enabled": True,
        "memory_index_loaded": index_loaded,
        "safety_memory_loaded": safety_loaded,
        "safety_memory_count": len(safety_ids),
        "safety_memory_ids": safety_ids,
        "safety_memory_required": safety_required,
        "safety_memory_status": safety_status,
    }

    print(json.dumps(snapshot, indent=2 if pretty else None))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FLAOS Bootstrap Context Resolver")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--json", action="store_true", help="Compact JSON output (default)")
    parser.add_argument("--diagnose", action="store_true", help="Validate and report system health status")
    args = parser.parse_args()
    sys.exit(build_snapshot(pretty=args.pretty, diagnose=args.diagnose))


if __name__ == "__main__":
    main()
