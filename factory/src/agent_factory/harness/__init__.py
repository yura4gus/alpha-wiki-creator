"""Native Temporal Agent Harness integration for the Alpha-Wiki Agent Factory.

Optional: enabled by the `harness` extra. The factory's execution path
(`agent_factory.workflows.TaskWorkflow`) is unchanged; this package adds a typed,
durable coordinator surface over it and the deterministic batch path. See
./README.md for the registry and commands.
"""

from .coordinator import FactoryCoordinatorAgent
from .models import (BatchCancellation, BatchStatus, BatchStatusQuery, BatchUnitStatus,
                     FactoryTaskSpec, SubmitBatch, SubmitTask, TaskApproval, TaskCancellation,
                     TaskStatus, TaskStatusQuery)
from .tools import (ALL_TOOLS, approve_task, cancel_batch, cancel_task, get_batch_status,
                    get_status, submit_batch, submit_task)

__all__ = [
    "ALL_TOOLS",
    "BatchCancellation",
    "BatchStatus",
    "BatchStatusQuery",
    "BatchUnitStatus",
    "FactoryCoordinatorAgent",
    "FactoryTaskSpec",
    "SubmitBatch",
    "SubmitTask",
    "TaskApproval",
    "TaskCancellation",
    "TaskStatus",
    "TaskStatusQuery",
    "approve_task",
    "cancel_batch",
    "cancel_task",
    "get_batch_status",
    "get_status",
    "submit_batch",
    "submit_task",
]
