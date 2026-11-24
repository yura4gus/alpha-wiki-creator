"""Live Temporal Cloud acceptance, gated by FACTORY_LIVE_CLOUD=1.

The API key is read from TEMPORAL_API_KEY, loaded by the invoking shell:

    set -a; . ~/.config/temporal-mcp/.env; set +a

It is never printed by this test. The namespace and endpoint default to the
existing factory dev target and can be overridden with
FACTORY_CLOUD_NAMESPACE / FACTORY_CLOUD_ADDRESS.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import pytest
from temporalio.api.workflowservice.v1 import DescribeNamespaceRequest
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

from agent_factory import receipts
from agent_factory.activities import ALL
from agent_factory.client import start_task, workflow_id
from agent_factory.connection import connect, resolve_connect_config
from agent_factory.workflows import TaskWorkflow
from conftest import agent, make_spec

CLOUD_ADDRESS = os.environ.get("FACTORY_CLOUD_ADDRESS", "alpha-dev.n3kw9.tmprl.cloud:7233")
CLOUD_NAMESPACE = os.environ.get("FACTORY_CLOUD_NAMESPACE", "alpha-dev.n3kw9")

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(
        os.environ.get("FACTORY_LIVE_CLOUD") != "1",
        reason="live Temporal Cloud; set FACTORY_LIVE_CLOUD=1 and TEMPORAL_API_KEY",
    ),
]


async def test_cloud_smoke_reaches_pr_open(origin, dirs, monkeypatch):
    api_key = os.environ.get("TEMPORAL_API_KEY")
    if not api_key:
        pytest.skip("TEMPORAL_API_KEY is not set; source ~/.config/temporal-mcp/.env first")

    monkeypatch.setenv("TEMPORAL_ADDRESS", CLOUD_ADDRESS)
    monkeypatch.setenv("TEMPORAL_NAMESPACE", CLOUD_NAMESPACE)
    monkeypatch.delenv("TEMPORAL_CONFIG_FILE", raising=False)
    monkeypatch.delenv("TEMPORAL_PROFILE", raising=False)
    monkeypatch.delenv("TEMPORAL_TLS", raising=False)
    # A local default left over from local runs must not route this to a dev server.
    monkeypatch.setenv("FACTORY_TEMPORAL_ADDRESS", "localhost:7233")

    resolved = resolve_connect_config()
    assert resolved["target_host"] == CLOUD_ADDRESS
    assert resolved["namespace"] == CLOUD_NAMESPACE
    assert resolved.get("api_key")  # loaded, never compared/rendered
    assert resolved["tls"]

    client = await connect()
    described_namespace = await client.workflow_service.describe_namespace(
        DescribeNamespaceRequest(namespace=CLOUD_NAMESPACE))
    assert described_namespace.namespace_info.name == CLOUD_NAMESPACE

    _, state = dirs
    queue = f"cloud-smoke-{uuid.uuid4().hex[:8]}"
    task_id = f"cloud-smoke-{uuid.uuid4().hex[:10]}"
    spec = make_spec(origin, queue, task_id, "src/a",
                     [agent("write", "src/a/one.txt", "cloud")],
                     require_approval=False)

    async with Worker(client, task_queue=queue, workflows=[TaskWorkflow], activities=ALL,
                      max_concurrent_activities=4):
        handle = await start_task(client, spec)
        assert handle.id == workflow_id(task_id)
        with pytest.raises(WorkflowAlreadyStartedError):
            await start_task(client, spec)  # no duplicate workflow id
        result = await asyncio.wait_for(handle.result(), timeout=240)
        described_workflow = await handle.describe()

    assert described_workflow.status.name == "COMPLETED"
    assert described_workflow.task_queue == queue
    assert result.status == "PR_OPEN"
    assert result.receipt_path and result.receipt_digest

    history = await handle.fetch_history()
    assert api_key not in history.to_json()

    path = receipts.receipt_path(state, handle.id)
    document = json.loads(path.read_text())
    assert receipts.validate(document) == []
    assert document["status"] == "PR_OPEN"
    assert document["workflow_id"] == handle.id
    assert document["digest"] == result.receipt_digest
    assert api_key not in path.read_text()

    prs = json.loads((state / "prs.json").read_text())
    assert len(prs) == 1
    assert next(iter(prs.values()))["number"] == 1
    assert api_key not in (state / "prs.json").read_text()

    print(json.dumps({
        "workflow_id": handle.id,
        "workflow_status": described_workflow.status.name,
        "task_queue": queue,
        "namespace": described_namespace.namespace_info.name,
        "receipt": str(path),
        "receipt_digest": document["digest"],
        "prs": len(prs),
    }, sort_keys=True))
