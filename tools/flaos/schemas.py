"""Typed dataclasses for FLAOS JSON schemas. Standard library only."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActiveWorkflowState:
    current_phase: str
    last_completed_task: str
    last_commit: str
    next_task: str
    next_workflow_tier: str
    blocked: bool
    batch_3c_started: bool
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActiveWorkflowState":
        return cls(
            current_phase=d.get("current_phase", ""),
            last_completed_task=d.get("last_completed_task", ""),
            last_commit=d.get("last_commit", ""),
            next_task=d.get("next_task", ""),
            next_workflow_tier=d.get("next_workflow_tier", "LOOP"),
            blocked=bool(d.get("blocked", False)),
            batch_3c_started=bool(d.get("batch_3c_started", False)),
            raw=d,
        )


@dataclass
class TaskQueueEntry:
    priority: int
    task_id: str
    status: str
    workflow_tier: str
    task_class: int
    description: str
    blocked_by: str | None
    allowed_scope: list[str]
    outputs: list[str]
    notes: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TaskQueueEntry":
        return cls(
            priority=int(d.get("priority", 99)),
            task_id=d.get("task_id", ""),
            status=d.get("status", "UNKNOWN"),
            workflow_tier=d.get("workflow_tier", "LOOP"),
            task_class=int(d.get("task_class", 3)),
            description=d.get("description", ""),
            blocked_by=d.get("blocked_by"),
            allowed_scope=d.get("allowed_scope", []),
            outputs=d.get("outputs", []),
            notes=d.get("notes", ""),
        )


@dataclass
class AgentPipeline:
    pipeline_id: str
    task_classes: list[int]
    workflow_tiers: list[str]
    risk_level: str
    role_sequence: list[str]
    required_evidence: str
    stop_conditions: list[str]
    full_accept_policy: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentPipeline":
        return cls(
            pipeline_id=d.get("pipeline_id", ""),
            task_classes=d.get("task_classes", []),
            workflow_tiers=d.get("workflow_tiers", []),
            risk_level=d.get("risk_level", "NONE"),
            role_sequence=d.get("role_sequence", []),
            required_evidence=d.get("required_evidence", "D"),
            stop_conditions=d.get("stop_conditions", []),
            full_accept_policy=d.get("full_accept_policy", ""),
        )


@dataclass
class ToolPipeline:
    pipeline_id: str
    workflow_tier: str
    task_classes: list[int]
    ordered_tool_sequence: list[str]
    required_evidence: str
    auto_repair_allowed: bool
    max_repairs: int
    stop_conditions: list[str]
    commit_policy: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ToolPipeline":
        return cls(
            pipeline_id=d.get("pipeline_id", ""),
            workflow_tier=d.get("workflow_tier", "LOOP"),
            task_classes=d.get("task_classes", []),
            ordered_tool_sequence=d.get("ordered_tool_sequence", []),
            required_evidence=d.get("required_evidence", "D"),
            auto_repair_allowed=bool(d.get("auto_repair_allowed", False)),
            max_repairs=int(d.get("max_repairs", 0)),
            stop_conditions=d.get("stop_conditions", []),
            commit_policy=d.get("commit_policy", "TYPE_C_ONLY"),
        )


@dataclass
class Skill:
    skill_id: str
    category: str
    purpose: str
    applicable_task_classes: list[int]
    workflow_tiers: list[str]
    required_tools: list[str]
    required_memory_reads: list[str]
    evidence_required: str
    stop_conditions: list[str]
    full_accept_allowed: bool
    auto_prepend_triggers: list[str]
    repair_policy: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Skill":
        return cls(
            skill_id=d.get("skill_id", ""),
            category=d.get("category", ""),
            purpose=d.get("purpose", ""),
            applicable_task_classes=d.get("applicable_task_classes", []),
            workflow_tiers=d.get("workflow_tiers", []),
            required_tools=d.get("required_tools", []),
            required_memory_reads=d.get("required_memory_reads", []),
            evidence_required=d.get("evidence_required", "D"),
            stop_conditions=d.get("stop_conditions", []),
            full_accept_allowed=bool(d.get("full_accept_allowed", True)),
            auto_prepend_triggers=d.get("auto_prepend_triggers", []),
            repair_policy=d.get("repair_policy", ""),
        )


@dataclass
class ExecutionSnapshot:
    task_id: str
    workflow_tier: str
    agent_pipeline_id: str
    role_sequence: list[str]
    tool_pipeline_id: str
    required_tools: list[str]
    skills: list[str]
    required_memory_reads: list[str]
    required_evidence: str
    max_repairs: int
    full_accept_allowed: bool
    stop_conditions: list[str]
    commit_policy: str
    final_output_format: str
    source_files_loaded: list[str]

@dataclass
class ToolRegistryEntry:
    tool_id: str
    category: str
    purpose: str
    command_or_action: str
    risk_level: str
    read_only: bool
    writes_files: bool
    allowed_workflow_tiers: list[str]
    allowed_roles: list[str]
    required_inputs: list[str]
    expected_outputs: list[str]
    stop_conditions: list[str]
    evidence_grade: str
    timeout_seconds: int
    full_accept_allowed: bool

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ToolRegistryEntry":
        return cls(
            tool_id=d.get("tool_id", ""),
            category=d.get("category", ""),
            purpose=d.get("purpose", ""),
            command_or_action=d.get("command_or_action", ""),
            risk_level=d.get("risk_level", "NONE"),
            read_only=bool(d.get("read_only", True)),
            writes_files=bool(d.get("writes_files", False)),
            allowed_workflow_tiers=d.get("allowed_workflow_tiers", []),
            allowed_roles=d.get("allowed_roles", []),
            required_inputs=d.get("required_inputs", []),
            expected_outputs=d.get("expected_outputs", []),
            stop_conditions=d.get("stop_conditions", []),
            evidence_grade=d.get("evidence_grade", "D"),
            timeout_seconds=int(d.get("timeout_seconds", 5)),
            full_accept_allowed=bool(d.get("full_accept_allowed", True)),
        )

