"""Offline checks for the native Temporal Agent Harness integration.

No Temporal server, no model: these cover the wire models, the schema/registry pair,
the four tool registrations and the coordinator contract. The end-to-end proof is in
`test_harness_integration.py`. Gated by the optional `harness` extra only.
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

pytest.importorskip("temporal_agent_harness")

from pydantic import ValidationError
from temporal_agent_harness.harness.agent_protocol import MidTurn
from temporal_agent_harness.harness.agent_schema import agent_schema
from temporal_agent_harness.harness.agent_workflow import (
    agent_handlers,
    agent_init_data,
    tool_activity,
)
from temporal_agent_harness.utils.task_queue import task_queue_name
from temporal_agent_harness.web.registry import load_agent_registry
from temporalio import workflow

from agent_factory.harness import (
    ALL_TOOLS,
    FactoryCoordinatorAgent,
    FactoryTaskSpec,
    SubmitTask,
    TaskApproval,
    TaskCancellation,
    TaskStatus,
    TaskStatusQuery,
    approve_task,
    cancel_task,
    get_status,
    submit_task,
)
from agent_factory.models import TaskSpec

FACTORY = Path(__file__).resolve().parents[1]
HARNESS = FACTORY / "harness"
SOURCE = FACTORY / "src" / "agent_factory" / "harness"

MINIMAL = {
    "task_id": "unit-1",
    "repo": "/tmp/origin.git",
    "agent_steps": [["true"]],
    "test_command": ["true"],
    "owned_paths": ["src/a"],
}


def test_factory_task_spec_mirrors_task_spec():
    """One conversion only: TaskSpec(**spec.model_dump())."""
    assert set(FactoryTaskSpec.model_fields) == {f.name for f in dataclasses.fields(TaskSpec)}
    assert FactoryTaskSpec(**MINIMAL).model_dump() == dataclasses.asdict(TaskSpec(**MINIMAL))
    # A non-default value for every field must survive the same conversion.
    full = FactoryTaskSpec(
        **MINIMAL,
        base_ref="release",
        context_files=["docs/architecture.md"],
        env_passthrough=["PATH", "HOME"],
        task_queue="factory-2",
        max_step_seconds=42,
        max_attempts=3,
        heartbeat_timeout_seconds=7,
        test_timeout_seconds=99,
        require_approval=False,
        approval_timeout_seconds=60,
        reviewer="opencode",
        review_model="opencode-go/deepseek-v4.1-flash",
        allow_free_review=True,
        pr_backend="local",
        pr_repo="owner/name",
        pr_title="title",
        xplan={"binding": {"run_id": "r"}, "observed": {"id": 1}},
        plugin_root="/plugin",
        harness2_evaluation="/tmp/h2.json",
        openflowkit_report="/tmp/ofk.json",
    )
    assert dataclasses.asdict(TaskSpec(**full.model_dump())) == full.model_dump()


def test_messages_roundtrip_through_json():
    submit = SubmitTask(spec=FactoryTaskSpec(**MINIMAL))
    assert SubmitTask.model_validate(submit.model_dump(mode="json")) == submit
    assert TaskStatusQuery(task_id="unit-1").model_dump() == {"task_id": "unit-1"}
    assert TaskCancellation(task_id="unit-1").task_id == "unit-1"

    approval = TaskApproval(task_id="unit-1", verdict="approve", by="owner", note="ship it")
    assert TaskApproval.model_validate_json(approval.model_dump_json()) == approval
    with pytest.raises(ValidationError):
        TaskApproval(task_id="unit-1", verdict="maybe", by="owner")

    status = TaskStatus(
        task_id="unit-1", workflow_id="task-unit-1", state="AWAITING_APPROVAL",
        temporal_status="RUNNING", receipt_status="RUNNING", receipt_digest="d" * 64,
        head_sha="a" * 40, review_verdict="APPROVE", reviewer="stub-rule-based",
        approval="approve by owner", evidence_status="MISSING", xplan_decision="SKIPPED",
        metrics={"step-0": {"seconds": 0.5}}, entries=["pinned", "review"])
    assert TaskStatus.model_validate_json(status.model_dump_json()) == status
    assert set(TaskStatus.model_fields) == {
        "task_id", "workflow_id", "state", "temporal_status", "receipt_status",
        "receipt_digest", "head_sha", "review_verdict", "reviewer", "approval",
        "evidence_status", "xplan_decision", "error", "metrics", "entries"}
    # Absent receipt data is empty, never invented.
    blank = TaskStatus(task_id="unit-1", workflow_id="task-unit-1")
    assert blank.error == "" and blank.state == "" and blank.metrics == {} and blank.entries == []


def test_registry_and_schema_are_present_and_consistent():
    registry_path = HARNESS / "agents.toml"
    schema_path = HARNESS / "FactoryCoordinatorAgent.schema.json"
    assert registry_path.is_file() and schema_path.is_file()

    registry = load_agent_registry(registry_path)  # validates the TOML and the schema path
    [agent] = registry.agents
    assert agent.key == "factory-coordinator"
    assert agent.workflow_type == "FactoryCoordinatorAgent"
    assert agent.task_queue == task_queue_name("factory-coordinator")
    assert agent.start is not None and agent.start.init_data is None  # only AgentConfig

    document = json.loads(schema_path.read_text())
    # The file is what a Console/client reads; fail if the models moved and it didn't.
    assert document == agent_schema(FactoryCoordinatorAgent)
    assert document["agent"] == "FactoryCoordinatorAgent"
    assert sorted(document["handlers"]) == ["approve_task", "cancel_task", "get_status",
                                           "submit_task"]
    assert document["init_data"] is None
    assert set(document["$defs"]["TaskStatus"]["properties"]) == set(TaskStatus.model_fields)
    assert set(document["$defs"]["FactoryTaskSpec"]["properties"]) == set(
        FactoryTaskSpec.model_fields)


def test_four_tools_are_registered_activity_tools():
    tools = [submit_task, get_status, approve_task, cancel_task]
    assert ALL_TOOLS == tools
    assert [tool.__name__ for tool in tools] == ["submit_task", "get_status", "approve_task",
                                                 "cancel_task"]
    names = set()
    for tool in tools:
        assert getattr(tool, "__agent_activity_tool__", False) is True
        activity = tool_activity(tool)  # raises if the decorator was forgotten
        name = activity.__temporal_activity_definition.name
        assert name == tool.__name__  # the Console event and activity share one name
        names.add(name)
    assert len(names) == 4
    # The tool inputs are the accepted messages, so the two contracts cannot drift.
    # Read them off the registered activity: the dispatcher's annotations stay stringized
    # (its __module__ is rewritten, its __globals__ are the harness's), while the activity
    # body carries the resolved hints.
    for tool, model in [(submit_task, SubmitTask), (get_status, TaskStatusQuery),
                        (approve_task, TaskApproval), (cancel_task, TaskCancellation)]:
        hints = tool_activity(tool).__annotations__
        assert hints["request"] is model
        assert hints["return"] is TaskStatus


def test_coordinator_exposes_four_enqueue_handlers():
    definition = workflow._Definition.from_class(FactoryCoordinatorAgent)
    assert definition.name == "FactoryCoordinatorAgent"
    assert agent_init_data(FactoryCoordinatorAgent) is None

    handlers = agent_handlers(FactoryCoordinatorAgent)
    assert sorted(handlers) == ["approve_task", "cancel_task", "get_status", "submit_task"]
    expected = {"submit_task": SubmitTask, "get_status": TaskStatusQuery,
                "approve_task": TaskApproval, "cancel_task": TaskCancellation}
    for name, handler in handlers.items():
        assert handler.input_type is expected[name]
        assert handler.output_type is TaskStatus
        assert handler.mid_turn is MidTurn.ENQUEUE
        assert handler.model_callable is False  # an operator surface, not a subagent tool
        assert handler.description.strip()


def test_harness_modules_import_no_model_provider():
    """The coordinator must never become a second model call path."""
    denylisted = {"openai", "anthropic", "google", "litellm", "agents", "strands", "cohere"}
    for path in [SOURCE / "models.py", SOURCE / "tools.py", SOURCE / "coordinator.py",
                 SOURCE / "worker.py"]:
        tree = ast.parse(path.read_text(), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
        assert imported.isdisjoint(denylisted), (path.name, imported & denylisted)
