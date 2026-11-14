"""Worker process: `python -m agent_factory.worker`.

Config (env): FACTORY_TEMPORAL_ADDRESS, FACTORY_TASK_QUEUE, FACTORY_WORK_ROOT,
FACTORY_STATE_DIR. One worker per host; give each host its own task queue when
worktrees must stay local to the host that created them.
"""

from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import ALL
from .workflows import TaskWorkflow


async def run(address: str, task_queue: str, max_activities: int = 10) -> None:
    client = await Client.connect(address)
    async with Worker(client, task_queue=task_queue, workflows=[TaskWorkflow], activities=ALL,
                      max_concurrent_activities=max_activities):
        await asyncio.Event().wait()


def main() -> None:
    asyncio.run(run(os.environ.get("FACTORY_TEMPORAL_ADDRESS", "localhost:7233"),
                    os.environ.get("FACTORY_TASK_QUEUE", "factory"),
                    int(os.environ.get("FACTORY_MAX_ACTIVITIES", "10"))))


if __name__ == "__main__":
    main()
