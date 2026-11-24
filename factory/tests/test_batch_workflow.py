"""DoD proof for the deterministic batch path with a real local Temporal server.

Fake Python/Bash scripts only. No model, no OpenCode, no PR, no review.
Covers SUCCESS, CRASH/RESUME, CANCEL, DUPLICATE, manifest/script tamper,
path traversal (offline suite), output cap and DQ failure.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Replayer, Worker

from agent_factory import receipts
from agent_factory.batch import checkpoints
from agent_factory.batch.activities import ALL as BATCH_ACTIVITIES
from agent_factory.batch.client import start_batch
from agent_factory.batch.manifest import compute_manifest_hash, load_job_spec
from agent_factory.batch.workflow import BatchWorkflow
from agent_factory.batch.util import sha256_file

pytestmark = pytest.mark.asyncio(loop_scope="module")

JOB = """\
import json, os, pathlib, sys
uid = os.environ["FACTORY_BATCH_UNIT_ID"]
root = pathlib.Path.cwd()
with open(root / "effects.log", "a") as handle:
    handle.write(uid + "\\n")
out = root / "out" / (uid + ".json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"unit": uid, "job": os.environ["FACTORY_BATCH_JOB_ID"],
                           "args": sys.argv[1:]}))
"""

SLOW_JOB = """\
import json, os, pathlib, sys, time
uid = os.environ["FACTORY_BATCH_UNIT_ID"]
root = pathlib.Path.cwd()
if uid == "u2":
    (root / "slow.pid").write_text(str(os.getpid()))
    time.sleep(30)
with open(root / "effects.log", "a") as handle:
    handle.write(uid + "\\n")
out = root / "out" / (uid + ".json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"unit": uid, "job": os.environ["FACTORY_BATCH_JOB_ID"],
                           "args": sys.argv[1:]}))
"""

DQ = """\
import json, pathlib
pathlib.Path("out/dq.json").write_text(json.dumps({"status": "PASS", "units": ["u1", "u2"]}))
"""

DQ_FAIL = """\
import json, pathlib
pathlib.Path("out/dq.json").write_text(json.dumps({"status": "MISS", "units": []}))
"""

DQ_MISSING = """\
print("no report written")
"""


@asynccontextmanager
async def batch_worker(server, queue: str):
    async with Worker(server.client, task_queue=queue, workflows=[BatchWorkflow],
                      activities=BATCH_ACTIVITIES, max_concurrent_activities=4):
        yield


def make_job(tmp_path: Path, job_id: str, queue: str, *, units: list[dict] | None = None,
             script_body: str = JOB, script_name: str = "job.py", runner_id: str = "python",
             dq: dict | None = None, heartbeat: int = 10,
             unit_timeout: int = 60) -> tuple[Path, Path, dict]:
    workspace = tmp_path / f"ws-{job_id}"
    workspace.mkdir(parents=True, exist_ok=True)
    script = workspace / script_name
    script.write_text(script_body)
    if runner_id in {"bash", "rust"}:
        script.chmod(0o755)
    units = units or [
        {"unit_id": "u1", "outputs": ["out/u1.json"], "resource_limits": {
            "timeout_seconds": unit_timeout, "cpu_seconds": unit_timeout,
            "memory_mb": 1024, "output_bytes": 1_000_000}},
        {"unit_id": "u2", "outputs": ["out/u2.json"], "resource_limits": {
            "timeout_seconds": unit_timeout, "cpu_seconds": unit_timeout,
            "memory_mb": 1024, "output_bytes": 1_000_000}},
    ]
    manifest = {
        "job_id": job_id,
        "runner_id": runner_id,
        "workspace": str(workspace),
        "script": script_name,
        "script_sha": sha256_file(script),
        "units": units,
        "task_queue": queue,
        "heartbeat_timeout_seconds": heartbeat,
        "retry_policy": {"max_attempts": 3, "initial_interval_seconds": 1},
    }
    if dq is not None:
        dq_script = workspace / dq["script"]
        dq_script.write_text(dq["body"])
        manifest["dq_contract"] = {
            "script": dq["script"], "script_sha": sha256_file(dq_script),
            "expected_exit": 0, "expected_json": dq["expected"],
            "report_path": "out/dq.json", "timeout_seconds": 30,
        }
    manifest["manifest_hash"] = compute_manifest_hash(manifest)
    path = tmp_path / f"{job_id}.json"
    path.write_text(json.dumps(manifest))
    return path, workspace, manifest


def receipt(state: Path, job_id: str) -> dict:
    return json.loads(receipts.receipt_path(state, f"batch-{job_id}").read_text())


def effects(workspace: Path) -> list[str]:
    path = workspace / "effects.log"
    return path.read_text().split() if path.exists() else []


async def test_success_with_checkpoints_dq_and_no_duplicate_side_effects(
        env, dirs, queue, tmp_path):
    _work, state = dirs
    dq = {"script": "dq.py", "body": DQ, "expected": {"status": "PASS"}}
    path, workspace, _manifest = make_job(tmp_path, "ok-batch", queue, dq=dq)
    spec = load_job_spec(path)
    async with batch_worker(env, queue):
        handle = await start_batch(env.client, spec)
        result = await asyncio.wait_for(handle.result(), timeout=120)

    assert result.status == "BATCH_SUCCESS", result.error
    assert result.job_id == "ok-batch" and result.dq.status == "PASS"
    assert [u.unit_id for u in result.units] == ["u1", "u2"]
    assert effects(workspace) == ["u1", "u2"]  # exactly once each
    doc = receipt(state, "ok-batch")
    assert doc["status"] == "BATCH_SUCCESS" and receipts.validate(doc) == []
    assert doc["digest"] == result.receipt_digest
    assert {"manifest", "unit-u1", "unit-u2", "dq"} <= set(doc["entries"])
    assert doc["entries"]["unit-u1"]["status"] == "COMPLETED"
    assert doc["entries"]["dq"]["status"] == "PASS"
    for unit in spec.units:
        checkpoint_path = state / "checkpoints" / "ok-batch" / f"{unit.unit_id}.json"
        assert checkpoint_path.is_file()
        view = checkpoints.read_checkpoint(state, spec, unit)
        assert view.valid and view.reason == "valid"
        assert view.checkpoint.outputs == {f"out/{unit.unit_id}.json":
                                           doc["entries"][f"unit-{unit.unit_id}"]["outputs"][
                                               f"out/{unit.unit_id}.json"]}
    await Replayer(workflows=[BatchWorkflow]).replay_workflow(await handle.fetch_history())


async def test_duplicate_submit_starts_one_workflow_and_one_side_effect(
        env, dirs, queue, tmp_path):
    _work, state = dirs
    path, workspace, _manifest = make_job(tmp_path, "dup-batch", queue)
    spec = load_job_spec(path)
    async with batch_worker(env, queue):
        handle = await start_batch(env.client, spec)
        with pytest.raises(WorkflowAlreadyStartedError):
            await start_batch(env.client, spec)
        result = await asyncio.wait_for(handle.result(), timeout=120)
        with pytest.raises(WorkflowAlreadyStartedError):
            await start_batch(env.client, spec)
    assert result.status == "BATCH_SUCCESS"
    assert effects(workspace) == ["u1", "u2"]
    assert len(list((state / "receipts").glob("batch-dup-batch.json"))) == 1
    assert (await env.client.get_workflow_handle("batch-dup-batch").describe()).status.name \
        == "COMPLETED"


async def test_cli_submit_status_and_cancel(env, dirs, queue, tmp_path):
    _work, state = dirs
    src = str(Path(__file__).resolve().parents[1] / "src")
    address = env.client.service_client.config.target_host

    def cli(*args: str) -> dict:
        proc = subprocess.run(
            [sys.executable, "-m", "agent_factory.batch", "--address", address, *args],
            env={**os.environ, "PYTHONPATH": src, "FACTORY_STATE_DIR": str(state),
                 "FACTORY_WORK_ROOT": str(tmp_path / "cli-work")},
            capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    fast_path, fast_ws, _manifest = make_job(tmp_path, "cli-ok", queue)
    slow_path, slow_ws, _manifest = make_job(tmp_path, "cli-cancel", queue,
                                             script_body=SLOW_JOB)
    async with batch_worker(env, queue):
        started = await asyncio.to_thread(cli, "submit", str(fast_path))
        assert started["workflow_id"] == "batch-cli-ok"
        for _ in range(120):
            status = await asyncio.to_thread(cli, "status", "cli-ok")
            if status["receipt_status"] == "BATCH_SUCCESS":
                break
            await asyncio.sleep(0.25)
        else:
            raise AssertionError(f"CLI status never reached BATCH_SUCCESS: {status}")
        assert status["state"] == "BATCH_SUCCESS"
        assert fast_ws.joinpath("effects.log").read_text().split() == ["u1", "u2"]

        await asyncio.to_thread(cli, "submit", str(slow_path))
        deadline = time.time() + 60
        while time.time() < deadline:
            if (slow_ws / "slow.pid").exists():
                break
            await asyncio.sleep(0.2)
        canceled = await asyncio.to_thread(cli, "cancel", "cli-cancel")
        assert canceled["receipt_status"] == "BATCH_CANCELED"
        assert canceled["state"] == "BATCH_CANCELED"


async def test_crash_resume_reuses_only_fenced_completed_units(
        env, dirs, queue, tmp_path):
    _work, state = dirs
    path, workspace, _manifest = make_job(
        tmp_path, "crash-batch", queue, heartbeat=5,
        units=[{"unit_id": "u1", "outputs": ["out/u1.json"], "resource_limits": {
            "timeout_seconds": 60, "cpu_seconds": 60, "memory_mb": 1024,
            "output_bytes": 1_000_000}}])
    spec = load_job_spec(path)
    src = str(Path(__file__).resolve().parents[1] / "src")
    address = env.client.service_client.config.target_host

    def spawn(work_root: Path, stderr_path: Path, faults: str = "") -> subprocess.Popen:
        environment = {
            **os.environ, "PYTHONPATH": src, "FACTORY_TEMPORAL_ADDRESS": address,
            "FACTORY_BATCH_TASK_QUEUE": queue, "FACTORY_WORK_ROOT": str(work_root),
            "FACTORY_STATE_DIR": str(state), "FACTORY_FAULTS": faults,
        }
        return subprocess.Popen([sys.executable, "-m", "agent_factory.batch_worker"],
                                env=environment, stdout=subprocess.DEVNULL,
                                stderr=open(stderr_path, "w"))

    work1 = tmp_path / "worker1"
    w1 = spawn(work1, tmp_path / "worker1.err", "batch_after_checkpoint@0=crash")
    try:
        handle = await start_batch(env.client, spec)
        deadline = time.time() + 60
        while w1.poll() is None and time.time() < deadline:
            await asyncio.sleep(0.2)
        assert w1.returncode == 137, "worker should die after writing unit 0's checkpoint"
        assert (state / "checkpoints" / "crash-batch" / "u1.json").is_file()
        assert effects(workspace) == ["u1"]
        import shutil
        shutil.rmtree(work1, ignore_errors=True)  # worker filesystem is ephemeral
        w2 = spawn(tmp_path / "worker2", tmp_path / "worker2.err")
        try:
            result = await asyncio.wait_for(handle.result(), timeout=120)
        finally:
            w2.kill()
            w2.wait()
    finally:
        if w1.poll() is None:
            w1.kill()
            w1.wait()

    assert result.status == "BATCH_SUCCESS", result.error
    doc = receipt(state, "crash-batch")
    assert receipts.validate(doc) == [] and doc["status"] == "BATCH_SUCCESS"
    assert doc["entries"]["unit-u1"]["status"] == "REUSED"  # checkpoint survived
    assert effects(workspace) == ["u1"]  # completed unit was not re-run
    assert doc["metrics"]["unit-u1"]["reused"] is True
    for unit in spec.units:
        assert checkpoints.read_checkpoint(state, spec, unit).valid
    await Replayer(workflows=[BatchWorkflow]).replay_workflow(await handle.fetch_history())


async def test_cancel_kills_process_group_and_freezes_batch_canceled(
        env, dirs, queue, tmp_path):
    _work, state = dirs
    path, workspace, _manifest = make_job(tmp_path, "cancel-batch", queue, heartbeat=5,
                                           script_body=SLOW_JOB)
    spec = load_job_spec(path)
    async with batch_worker(env, queue):
        handle = await start_batch(env.client, spec)
        deadline = time.time() + 60
        while time.time() < deadline:
            if (workspace / "slow.pid").exists():
                break
            await asyncio.sleep(0.2)
        else:
            raise AssertionError("slow unit never started")
        pid = int((workspace / "slow.pid").read_text())
        await handle.cancel()
        with pytest.raises(WorkflowFailureError):
            await handle.result()
    time.sleep(0.5)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    doc = receipt(state, "cancel-batch")
    assert doc["status"] == "BATCH_CANCELED" and receipts.validate(doc) == []
    assert "canceled" in doc["entries"]
    assert (state / "checkpoints" / "cancel-batch" / "u1.json").is_file()
    assert not (state / "checkpoints" / "cancel-batch" / "u2.json").exists()
    assert effects(workspace) == ["u1"]


@pytest.mark.parametrize("tamper", ["manifest", "script"])
async def test_manifest_or_script_tamper_fails_before_any_unit_runs(
        env, dirs, queue, tmp_path, tamper):
    _work, state = dirs
    path, workspace, manifest = make_job(tmp_path, f"tamper-{tamper}", queue)
    spec = load_job_spec(path)
    if tamper == "manifest":
        changed = dict(manifest, job_id="other")
        path.write_text(json.dumps(changed))  # hash no longer matches
    else:
        with open(workspace / "job.py", "a") as handle:
            handle.write("print('tampered')\n")
    async with batch_worker(env, queue):
        result = await asyncio.wait_for(
            (await start_batch(env.client, spec)).result(), timeout=60)
    assert result.status == "BATCH_FAILED"
    assert "BatchManifestInvalid" in result.error
    doc = receipt(state, f"tamper-{tamper}")
    assert doc["status"] == "BATCH_FAILED" and receipts.validate(doc) == []
    assert "failure" in doc["entries"] and "unit-u1" not in doc["entries"]
    assert effects(workspace) == []


async def test_output_cap_fails_without_a_checkpoint(env, dirs, queue, tmp_path):
    _work, state = dirs
    path, workspace, _manifest = make_job(
        tmp_path, "cap-batch", queue, runner_id="bash", script_name="spam.sh",
        script_body="#!/bin/bash\nyes spam\n",
        units=[{"unit_id": "u1", "outputs": [], "resource_limits": {
            "timeout_seconds": 20, "cpu_seconds": 20, "memory_mb": 1024,
            "output_bytes": 1024}}])
    spec = load_job_spec(path)
    async with batch_worker(env, queue):
        result = await asyncio.wait_for(
            (await start_batch(env.client, spec)).result(), timeout=90)
    assert result.status == "BATCH_FAILED"
    assert "output" in result.error.lower()
    doc = receipt(state, "cap-batch")
    assert doc["status"] == "BATCH_FAILED" and receipts.validate(doc) == []
    assert not (state / "checkpoints" / "cap-batch" / "u1.json").exists()


@pytest.mark.parametrize("body,expected,status", [
    (DQ_FAIL, {"status": "PASS"}, "FAIL"),
    (DQ_MISSING, {"status": "PASS"}, "MISSING"),
])
async def test_dq_failure_is_explicit_and_fails_the_job(
        env, dirs, queue, tmp_path, body, expected, status):
    _work, state = dirs
    job_id = f"dq-{status.lower()}"
    dq = {"script": "dq.py", "body": body, "expected": expected}
    path, _workspace, _manifest = make_job(tmp_path, job_id, queue, dq=dq)
    spec = load_job_spec(path)
    async with batch_worker(env, queue):
        result = await asyncio.wait_for(
            (await start_batch(env.client, spec)).result(), timeout=120)
    assert result.status == "BATCH_FAILED"
    assert result.dq.status == status  # missing is reported, not guessed as PASS
    doc = receipt(state, job_id)
    assert doc["status"] == "BATCH_FAILED" and receipts.validate(doc) == []
    assert doc["entries"]["dq"]["status"] == status
    assert "unit-u1" in doc["entries"] and "unit-u2" in doc["entries"]
