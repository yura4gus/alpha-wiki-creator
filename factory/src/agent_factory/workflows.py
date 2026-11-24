"""One durable TaskWorkflow per task. Workflow ID: `task-<task_id>`.

State machine: pin -> context -> agent steps (checkpointed) -> tests -> review
-> [human approval] -> PR -> xPlan dry-run -> receipt. The workflow holds no
process while it waits for approval; worker loss is recovered by activity
heartbeat timeout plus checkpoint resume.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, is_cancelled_exception

with workflow.unsafe.imports_passed_through():
    from . import activities as act
    from .models import Decision, PRRequest, ReviewRequest, TaskResult, TaskSpec

SHORT = dict(
    start_to_close_timeout=timedelta(minutes=2),
    retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5),
)


@workflow.defn
class TaskWorkflow:
    def __init__(self) -> None:
        self._state = "PENDING"
        self._decision: Decision | None = None

    @workflow.query
    def state(self) -> str:
        return self._state

    @workflow.update
    async def decide(self, decision: Decision) -> str:
        self._decision = decision
        return f"{decision.verdict} recorded"

    @decide.validator
    def _check_decision(self, decision: Decision) -> None:
        if self._state != "AWAITING_APPROVAL":
            raise ValueError(f"task is {self._state}, not awaiting approval")
        if decision.verdict not in ("approve", "reject"):
            raise ValueError("verdict must be approve or reject")
        if not decision.by:
            raise ValueError("decision needs an identified approver")

    async def _rec(self, key: str, data: dict, metrics: dict | None = None) -> None:
        await workflow.execute_activity(
            act.record_step, args=[key, json.dumps(data, sort_keys=True),
                                   json.dumps(metrics) if metrics else ""], **SHORT)

    async def _finish(self, spec: TaskSpec, status: str, result: TaskResult) -> TaskResult:
        self._state = status
        await workflow.execute_activity(act.cleanup_worktree, spec, **SHORT)
        receipt = await workflow.execute_activity(act.finalize_receipt, status, **SHORT)
        result.status = status
        result.receipt_path, result.receipt_digest = receipt["path"], receipt["digest"]
        return result

    @workflow.run
    async def run(self, spec: TaskSpec) -> TaskResult:
        result = TaskResult(status="RUNNING")
        try:
            return await self._run(spec, result)
        except (asyncio.CancelledError, ActivityError) as exc:
            if is_cancelled_exception(exc):  # also when cancel surfaces through a running activity
                await self._rec("canceled", {"at_state": self._state})
                await self._finish(spec, "CANCELED", result)
                raise
            cause = exc.cause
            result.error = f"{exc.activity_type}: {type(cause).__name__}: {cause}"[:500]
            await self._rec("failure", {"activity": exc.activity_type,
                                        "cause": type(cause).__name__})
            return await self._finish(spec, "FAILED", result)

    async def _run(self, spec: TaskSpec, result: TaskResult) -> TaskResult:
        self._state = "PINNING"
        base = await workflow.execute_activity(act.pin_snapshot, spec, **SHORT)
        result.base_sha = base
        await self._rec("pinned", {"base_sha": base, "base_ref": spec.base_ref})

        self._state = "CONTEXT"
        ctx = await workflow.execute_activity(act.build_context, args=[spec, base], **SHORT)
        await self._rec("context", {"sources": ctx.sources})

        checkpoint = base
        for index in range(len(spec.agent_steps)):
            self._state = f"AGENT_STEP_{index}"
            step = await workflow.execute_activity(
                act.agent_step, args=[spec, index, checkpoint, ctx.text],
                start_to_close_timeout=timedelta(seconds=spec.max_step_seconds),
                heartbeat_timeout=timedelta(seconds=spec.heartbeat_timeout_seconds),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1), maximum_attempts=spec.max_attempts,
                    non_retryable_error_types=["OwnershipViolation"]),
                cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED)
            checkpoint = step.sha
            await self._rec(f"step-{index}", {"sha": step.sha, "changed": step.changed},
                            {"seconds": round(step.seconds, 2), "reused": step.reused,
                             "exit_code": step.exit_code, "telemetry": step.usage})
        result.head_sha = checkpoint

        self._state = "TESTING"
        tests = await workflow.execute_activity(
            act.run_tests, args=[spec, checkpoint],
            start_to_close_timeout=timedelta(seconds=spec.test_timeout_seconds + 30),
            heartbeat_timeout=timedelta(seconds=spec.heartbeat_timeout_seconds),
            retry_policy=RetryPolicy(maximum_attempts=2))
        await self._rec("tests", {"passed": tests.passed, "exit_code": tests.exit_code},
                        {"seconds": round(tests.seconds, 2)})
        if not tests.passed:
            result.error = tests.log_tail[-300:]
            return await self._finish(spec, "FAILED_TESTS", result)

        self._state = "REVIEW"
        evidence = await workflow.execute_activity(act.collect_evidence, spec, **SHORT)
        await self._rec("evidence", {"status": evidence.status, "sources": evidence.sources,
                                     "note": evidence.note})
        context_text = ctx.text
        if evidence.refs:
            context_text += "\n\n## External evidence (read-only)\n" + "\n".join(
                f"- {ref}" for ref in evidence.refs)
        verdict = await workflow.execute_activity(
            act.review, args=[spec, ReviewRequest(base, checkpoint, context_text, tests.passed,
                                                  tests.log_tail)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3))
        result.review = asdict(verdict)
        review_data = dict(result.review)
        review_usage = review_data.pop("telemetry", {})
        result.review.pop("telemetry", None)
        await self._rec("review", review_data,
                        {"telemetry": review_usage} if review_usage else None)
        evidence_refs = [f"receipt:{workflow.info().workflow_id}", f"commit:{checkpoint}",
                         *evidence.refs]
        if verdict.diff_sha256:
            evidence_refs.append(f"diff:sha256:{verdict.diff_sha256}")
        if verdict.verdict == "BLOCKED":
            result.error = verdict.findings
            return await self._finish(spec, "BLOCKED_REVIEW", result)
        if verdict.verdict == "CHANGES":
            plan = await workflow.execute_activity(
                act.reconcile_dry_run, args=[spec, "rework", checkpoint, evidence_refs,
                                             verdict.findings], **SHORT)
            await self._rec("xplan_dry_run", plan)
            result.error = verdict.findings
            return await self._finish(spec, "CHANGES_REQUESTED", result)
        if verdict.verdict != "APPROVE":
            result.error = f"unknown review verdict {verdict.verdict!r}; refusing to ship"
            return await self._finish(spec, "BLOCKED_REVIEW", result)

        if spec.require_approval:
            self._state = "AWAITING_APPROVAL"
            try:
                await workflow.wait_condition(
                    lambda: self._decision is not None,
                    timeout=timedelta(seconds=spec.approval_timeout_seconds))
            except asyncio.TimeoutError:
                await self._rec("approval", {"verdict": "timeout"})
                return await self._finish(spec, "APPROVAL_TIMEOUT", result)
            decision = self._decision
            await self._rec("approval", {"verdict": decision.verdict, "by": decision.by,
                                         "note": decision.note})
            if decision.verdict == "reject":
                return await self._finish(spec, "REJECTED", result)

        self._state = "OPENING_PR"
        pr = await workflow.execute_activity(
            act.open_pr, args=[spec, PRRequest(checkpoint, verdict.findings)], **SHORT)
        result.pr = pr
        await self._rec("pr", {"head": pr["head"], "head_sha": checkpoint}, {"number": pr.get("number")})

        plan = await workflow.execute_activity(
            act.reconcile_dry_run, args=[spec, "worker_finished", checkpoint, evidence_refs, ""], **SHORT)
        await self._rec("xplan_dry_run", plan)
        return await self._finish(spec, "PR_OPEN", result)
