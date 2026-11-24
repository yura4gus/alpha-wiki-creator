"""Batch worker: `python -m agent_factory.batch_worker`.

Polls `FACTORY_BATCH_TASK_QUEUE` (default `bsc-batch`) with only the batch
workflow and its activities. No model, no harness, no reviewer, no PR adapter.
"""

from __future__ import annotations

import asyncio
import os

from temporalio.worker import Worker

from .batch.activities import ALL
from .batch.models import DEFAULT_TASK_QUEUE
from .batch.workflow import BatchWorkflow
from .connection import connect


async def run(address: str | None = None, task_queue: str | None = None,
              max_activities: int | None = None) -> None:
    client = await connect(address)
    queue = task_queue or os.environ.get("FACTORY_BATCH_TASK_QUEUE", DEFAULT_TASK_QUEUE)
    limit = max_activities or int(os.environ.get("FACTORY_BATCH_MAX_ACTIVITIES", "4"))
    async with Worker(client, task_queue=queue, workflows=[BatchWorkflow], activities=ALL,
                      max_concurrent_activities=limit):
        print(f"Batch worker ready: taskQueue={queue} workflows={[BatchWorkflow.__name__]}",
              flush=True)
        await asyncio.Event().wait()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
