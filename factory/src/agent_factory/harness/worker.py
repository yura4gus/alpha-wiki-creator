"""Coordinator worker: `python -m agent_factory.harness.worker`.

Connects with the factory's connection resolver (SDK `TEMPORAL_*` / Cloud profile plus
`FACTORY_TEMPORAL_ADDRESS`) and the harness plugin, which supplies the pydantic data
converter, the large-payload offload and the four tool activities. Polls
`FACTORY_HARNESS_TASK_QUEUE` (default `factory-coordinator`). No model plugin is
registered: the coordinator never calls a model.
"""

from __future__ import annotations

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker
from temporal_agent_harness.plugin import AgentHarnessPlugin
from temporal_agent_harness.utils.task_queue import task_queue_name

from ..connection import resolve_connect_config
from .coordinator import FactoryCoordinatorAgent
from .tools import ALL_TOOLS

DEFAULT_TASK_QUEUE = "factory-coordinator"
DEFAULT_ADDRESS = "localhost:7233"


async def run(address: str | None = None, task_queue: str | None = None) -> None:
    # resolve_connect_config() is the factory's one connection rule and calls
    # ClientConfig.load_client_connect_config() whenever a TEMPORAL_* profile is present.
    connect_config = resolve_connect_config(address)
    client = await Client.connect(**connect_config, plugins=[AgentHarnessPlugin(tools=ALL_TOOLS)])
    queue = task_queue or task_queue_name(
        os.environ.get("FACTORY_HARNESS_TASK_QUEUE", DEFAULT_TASK_QUEUE))
    worker = Worker(client, task_queue=queue, workflows=[FactoryCoordinatorAgent])
    print(
        "Factory coordinator worker ready: "
        f"address={connect_config.get('target_host', DEFAULT_ADDRESS)} "
        f"namespace={client.namespace} "
        f"taskQueue={queue} "
        f"workflow={FactoryCoordinatorAgent.__name__} "
        f"tools={[tool.__name__ for tool in ALL_TOOLS]}",
        flush=True,
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s", force=True)
    asyncio.run(run())


if __name__ == "__main__":
    main()
