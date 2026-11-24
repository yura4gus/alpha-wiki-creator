"""Wire models for the harness surface.

The harness speaks pydantic models; the TaskWorkflow speaks dataclasses. These models are
the adapter: `FactoryTaskSpec` carries exactly the fields of `agent_factory.models.TaskSpec`
(so `TaskSpec(**spec.model_dump())` is the only conversion), and `TaskStatus` is a
projection of the durable receipt plus the live Temporal state.

Deliberately no `from __future__ import annotations`: these models cross the pydantic data
converter, and postponing annotations would leave their types unresolved until
`model_rebuild()`, which the harness/plugin paths never call.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FactoryTaskSpec(BaseModel):
    """One factory task, field-for-field equal to `agent_factory.models.TaskSpec`.

    Defaults are copied from TaskSpec; `test_harness_units.py` asserts the two
    definitions stay in sync.
    """

    task_id: str = Field(description="Task identity; the workflow id is `task-<task_id>`.")
    repo: str = Field(description="Git URL or path used as origin; checkpoints are pushed here.")
    # argv per step; the native CLI loops stay intact.
    agent_steps: list[list[str]]
    test_command: list[str]
    owned_paths: list[str] = Field(description="Repo-relative prefixes this task may change.")
    base_ref: str = "main"
    context_files: list[str] = Field(default_factory=list)
    # Variable *names* only; values stay in the worker environment.
    env_passthrough: list[str] = Field(default_factory=list)
    task_queue: str = "factory"
    max_step_seconds: int = 900
    max_attempts: int = 2
    heartbeat_timeout_seconds: int = 30
    test_timeout_seconds: int = 600
    require_approval: bool = True
    approval_timeout_seconds: int = 86400
    reviewer: str = "stub"
    review_model: str = "opencode-go/deepseek-v4.1-flash"
    allow_free_review: bool = False
    pr_backend: str = "local"
    pr_repo: str | None = None
    pr_title: str = ""
    xplan: dict[str, Any] | None = None
    plugin_root: str | None = None
    harness2_evaluation: str | None = None
    openflowkit_report: str | None = None


class SubmitTask(BaseModel):
    """Ask the coordinator to start one `TaskWorkflow` (`task-<task_id>`)."""

    spec: FactoryTaskSpec


class TaskStatusQuery(BaseModel):
    """Ask the coordinator for one task's live state and durable receipt."""

    task_id: str = Field(description="Task identity; the workflow id is `task-<task_id>`.")


class TaskApproval(BaseModel):
    """Forward a human decision to `TaskWorkflow.decide`, the durable approval authority."""

    task_id: str
    verdict: Literal["approve", "reject"]
    by: str = Field(description="Identified approver, recorded in the receipt.")
    note: str = ""


class TaskCancellation(BaseModel):
    """Cancel a running factory task through the workflow's own cancellation path."""

    task_id: str


class TaskStatus(BaseModel):
    """One task's Temporal state plus the durable receipt fields the factory records.

    `error` is set when the operation failed or the task is unknown; an empty `error`
    with a state means the read succeeded. Nothing here is fabricated: absent receipt
    fields stay empty strings.
    """

    task_id: str
    workflow_id: str
    state: str = Field(
        default="", description="`TaskWorkflow.state` (PENDING..PR_OPEN), or the receipt's status.")
    temporal_status: str = Field(
        default="", description="Temporal execution status (RUNNING, COMPLETED, CANCELED, ...).")
    receipt_status: str = ""
    receipt_digest: str = ""
    head_sha: str = Field(default="", description="Last checkpoint SHA, else the pinned base SHA.")
    review_verdict: str = ""
    reviewer: str = ""
    approval: str = Field(
        default="", description="Recorded decision as `<verdict> by <approver> (<note>)`.")
    evidence_status: str = ""
    xplan_decision: str = ""
    error: str = ""
    metrics: dict[str, dict[str, Any]] = Field(default_factory=dict)
    entries: list[str] = Field(
        default_factory=list, description="Receipt entry keys in recorded order.")
