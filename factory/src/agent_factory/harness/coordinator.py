"""`FactoryCoordinatorAgent`: a deterministic, durable coordinator over TaskWorkflow.

The agent is the native Temporal Agent Harness surface (typed messages, a workflow stream,
the Console/session manager), not a second executor:

- TaskWorkflow still owns pin -> context -> steps -> tests -> review -> approval -> PR.
- `agent_factory.harness.tools` is the only bridge to it.
- Tool approval is skipped here because `TaskWorkflow.decide` is the approval authority;
  a harness approval gate would be a second queue for the same decision.
- No model is called. Each handler dispatches exactly one tool through
  `runner.run_tool`, so the Console receives real `tool_start`/`tool_end` events.
"""

from __future__ import annotations

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporalio.contrib.workflow_streams import WorkflowStream

    from temporal_agent_harness.harness import agent
    from temporal_agent_harness.harness.agent_protocol import (
        AgentConfig,
        MidTurn,
        ToolApprovalPolicy,
    )
    from temporal_agent_harness.harness.agent_workflow import AgentWorkflowRunner

    from . import tools
    from .models import (SubmitTask, TaskApproval, TaskCancellation, TaskStatus,
                         TaskStatusQuery)


@agent.defn(name="FactoryCoordinatorAgent")
class FactoryCoordinatorAgent:
    """Operator surface for the Alpha-Wiki factory tasks.

    Accepted messages: `submit_task`, `get_status`, `approve_task`, `cancel_task`.
    Every handler is ENQUEUE (a second request waits its turn rather than failing or
    joining) and none is model-callable: a model must not drive task admission or
    approvals.
    """

    @agent.init
    def __init__(self, config: AgentConfig) -> None:
        self._runner = AgentWorkflowRunner(
            config,
            stream=WorkflowStream(),
            # Factory TaskWorkflow owns the human approval decision. Skipping the harness
            # tool gate avoids a second approval queue; it does not skip task approval.
            approval_policy_default=ToolApprovalPolicy.dangerously_skip_all(),
        )

    async def _dispatch(self, tool, request):
        """One tool call with a per-invocation id, so Console events correlate."""
        return await self._runner.run_tool(str(workflow.uuid4()), tool, request)

    @agent.accepts(mid_turn=MidTurn.ENQUEUE, model_callable=False)
    async def submit_task(self, request: SubmitTask) -> TaskStatus:
        """Start one Alpha-Wiki factory task (its own TaskWorkflow, id `task-<task_id>`).
        Re-submitting a task id that already exists fails with REJECT_DUPLICATE and returns
        that task's status; it never starts a second run."""
        return await self._dispatch(tools.submit_task, request)

    @agent.accepts(mid_turn=MidTurn.ENQUEUE, model_callable=False)
    async def get_status(self, request: TaskStatusQuery) -> TaskStatus:
        """Read one task's live workflow state and durable receipt (status, review verdict,
        approval, evidence, xPlan decision, checkpoint SHA). Read-only."""
        return await self._dispatch(tools.get_status, request)

    @agent.accepts(mid_turn=MidTurn.ENQUEUE, model_callable=False)
    async def approve_task(self, request: TaskApproval) -> TaskStatus:
        """Apply an operator approval or rejection to a task waiting in AWAITING_APPROVAL.
        The decision goes through TaskWorkflow.decide, the factory's durable approval
        authority, and is recorded in the receipt with the approver's name."""
        return await self._dispatch(tools.approve_task, request)

    @agent.accepts(mid_turn=MidTurn.ENQUEUE, model_callable=False)
    async def cancel_task(self, request: TaskCancellation) -> TaskStatus:
        """Cancel one running task through its TaskWorkflow, wait for it to close, and
        return the finalized CANCELED receipt status."""
        return await self._dispatch(tools.cancel_task, request)
