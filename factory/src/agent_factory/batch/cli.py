"""Operator CLI: `python -m agent_factory.batch submit|status|cancel`."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from temporalio.exceptions import WorkflowAlreadyStartedError

from ..connection import connect
from .client import cancel_batch, start_batch
from .manifest import BatchManifestError, load_job_spec
from .status import batch_status


def _print(value: dict) -> None:
    print(json.dumps(value, sort_keys=True))


async def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent_factory.batch")
    parser.add_argument("--address", default=None,
                        help="Temporal address override (default: FACTORY_TEMPORAL_ADDRESS, "
                             "TEMPORAL_* env config, then localhost:7233)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    submit = sub.add_parser("submit", help="validate a manifest and start batch-<job_id>")
    submit.add_argument("manifest")
    status = sub.add_parser("status", help="show workflow state and durable receipt")
    status.add_argument("job_id")
    cancel = sub.add_parser("cancel", help="cancel batch-<job_id> and print its receipt")
    cancel.add_argument("job_id")
    args = parser.parse_args(argv)

    try:
        client = await connect(args.address)
        if args.cmd == "submit":
            spec = await asyncio.to_thread(load_job_spec, args.manifest)
            handle = await start_batch(client, spec)
            _print({"job_id": spec.job_id, "workflow_id": handle.id,
                    "task_queue": spec.task_queue, "state": "SUBMITTED"})
            return 0
        if args.cmd == "status":
            _print(await batch_status(client, args.job_id))
            return 0
        _print(await cancel_batch(client, args.job_id))
        return 0
    except WorkflowAlreadyStartedError as exc:
        _print({"error": f"workflow already started: {exc}", "state": "DUPLICATE"})
        return 1
    except BatchManifestError as exc:
        _print({"error": str(exc), "state": "INVALID_MANIFEST"})
        return 2


def main() -> None:
    sys.exit(asyncio.run(_main(sys.argv[1:])))


__all__ = ["main"]
