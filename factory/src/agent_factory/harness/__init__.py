"""Native Temporal Agent Harness integration for the Alpha-Wiki Agent Factory.

Optional: enabled by the `harness` extra. The factory's execution path
(`agent_factory.workflows.TaskWorkflow`) is unchanged; this package adds a typed,
durable coordinator surface over it. See ./README.md for the registry and commands.
"""

from .coordinator import FactoryCoordinatorAgent
from .models import (FactoryTaskSpec, SubmitTask, TaskApproval, TaskCancellation, TaskStatus,
                     TaskStatusQuery)
from .tools import ALL_TOOLS, approve_task, cancel_task, get_status, submit_task

__all__ = [
    "ALL_TOOLS",
    "FactoryCoordinatorAgent",
    "FactoryTaskSpec",
    "SubmitTask",
    "TaskApproval",
    "TaskCancellation",
    "TaskStatus",
    "TaskStatusQuery",
    "approve_task",
    "cancel_task",
    "get_status",
    "submit_task",
]
