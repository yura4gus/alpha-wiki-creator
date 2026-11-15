"""Admission control and operator entry points for TaskWorkflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from temporalio.client import Client, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy

from .connection import connect
from .models import Decision, TaskSpec
from .workflows import TaskWorkflow


def workflow_id(task_id: str) -> str:
    return f"task-{task_id}"


def validate_batch(specs: list[TaskSpec]) -> None:
    """Reject empty contracts, duplicate ids and overlapping file ownership."""
    seen: dict[str, str] = {}
    for spec in specs:
        if not (spec.agent_steps and spec.test_command and spec.owned_paths):
            raise ValueError(f"{spec.task_id}: agent_steps, test_command and owned_paths are required")
        if spec.reviewer not in {"stub", "opencode"}:
            raise ValueError(f"{spec.task_id}: unknown reviewer {spec.reviewer!r}")
        if spec.review_model.endswith("-free") and not spec.allow_free_review:
            raise ValueError(f"{spec.task_id}: free review model needs allow_free_review=true")
        if spec.pr_backend == "gh" and spec.reviewer != "opencode":
            raise ValueError(f"{spec.task_id}: a real PR needs the independent OpenCode reviewer")
        if any(p.startswith("/") or ".." in p.split("/") for p in spec.owned_paths):
            raise ValueError(f"{spec.task_id}: owned_paths must be repo-relative")
        if spec.task_id in seen:
            raise ValueError(f"duplicate task_id {spec.task_id}")
        seen[spec.task_id] = spec.repo
    for i, a in enumerate(specs):
        for b in specs[i + 1:]:
            if a.repo != b.repo:
                continue
            for pa in a.owned_paths:
                for pb in b.owned_paths:
                    pa_, pb_ = pa.rstrip("/") + "/", pb.rstrip("/") + "/"
                    if pa_.startswith(pb_) or pb_.startswith(pa_):
                        raise ValueError(f"ownership overlap: {a.task_id}:{pa} vs {b.task_id}:{pb}")


async def start_task(client: Client, spec: TaskSpec) -> WorkflowHandle:
    validate_batch([spec])
    return await client.start_workflow(
        TaskWorkflow.run, spec, id=workflow_id(spec.task_id), task_queue=spec.task_queue,
        id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        id_conflict_policy=WorkflowIDConflictPolicy.FAIL)


async def start_batch(client: Client, specs: list[TaskSpec]) -> list[WorkflowHandle]:
    validate_batch(specs)
    return [await start_task(client, spec) for spec in specs]


async def decide(client: Client, task_id: str, verdict: str, by: str, note: str = "") -> str:
    handle = client.get_workflow_handle(workflow_id(task_id))
    return await handle.execute_update(TaskWorkflow.decide, Decision(verdict, by, note))


def _spec(path: str) -> TaskSpec:
    return TaskSpec(**json.loads(open(path).read()))


async def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent-factory")
    parser.add_argument("--address", default=None,
                        help="Temporal address override (default: FACTORY_TEMPORAL_ADDRESS, "
                             "TEMPORAL_* env config, then localhost:7233)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("spec", nargs="+")
    d = sub.add_parser("decide")
    d.add_argument("task_id"), d.add_argument("verdict", choices=["approve", "reject"])
    d.add_argument("--by", required=True), d.add_argument("--note", default="")
    st = sub.add_parser("status")
    st.add_argument("task_id")
    c = sub.add_parser("cancel")
    c.add_argument("task_id")
    args = parser.parse_args(argv)
    client = await connect(args.address)
    if args.cmd == "start":
        for handle in await start_batch(client, [_spec(p) for p in args.spec]):
            print(handle.id)
    elif args.cmd == "decide":
        print(await decide(client, args.task_id, args.verdict, args.by, args.note))
    elif args.cmd == "status":
        handle = client.get_workflow_handle(workflow_id(args.task_id))
        print(json.dumps({"state": await handle.query(TaskWorkflow.state),
                          "status": (await handle.describe()).status.name}))
    elif args.cmd == "cancel":
        await client.get_workflow_handle(workflow_id(args.task_id)).cancel()
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main(sys.argv[1:])))


if __name__ == "__main__":
    main()
