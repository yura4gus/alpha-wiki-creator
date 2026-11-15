import asyncio
import json
import socket
import sys
import types

import pytest

from agent_factory import launcher, receipts


def task(**kw):
    base = dict(task_id="up", repo="/repo", agent_steps=[["true"]], test_command=["true"],
                owned_paths=["app"])
    base.update(kw)
    return base


def write_specs(tmp_path, *docs):
    paths = []
    for i, doc in enumerate(docs):
        path = tmp_path / f"task-{i}.json"
        path.write_text(json.dumps(doc))
        paths.append(str(path))
    return paths


def test_load_specs_accepts_one_or_many(tmp_path):
    specs = launcher.load_specs(write_specs(tmp_path, task(), [task(task_id="up2", owned_paths=["lib"])]))
    assert [s.task_id for s in specs] == ["up", "up2"]


def test_load_specs_rejects_duplicate_ids_and_overlap(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        launcher.load_specs(write_specs(tmp_path, task(), task()))
    with pytest.raises(ValueError, match="overlap"):
        launcher.load_specs(write_specs(tmp_path, task(owned_paths=["app"]),
                                        task(task_id="b", owned_paths=["app/api"])))


def test_receipt_summary_measures_step_time_and_review(tmp_path):
    receipts.record(tmp_path, "task-up", "up", "step-0", {"sha": "a" * 40}, {"seconds": 2.5})
    receipts.record(tmp_path, "task-up", "up", "tests", {"passed": True}, {"seconds": 1.5})
    receipts.record(tmp_path, "task-up", "up", "review", {"verdict": "APPROVE",
                                                          "reviewer": "opencode:m"})
    receipts.finalize(tmp_path, "task-up", "up", "PR_OPEN")
    summary = launcher._receipt_summary(receipts.receipt_path(tmp_path, "task-up"))
    assert summary["status"] == "PR_OPEN" and summary["measured_step_seconds"] == 4.0
    assert summary["review"] == "APPROVE" and summary["reviewer"] == "opencode:m"
    assert len(summary["digest"]) == 16


def test_receipt_command_reports_invalid_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FACTORY_STATE_DIR", str(tmp_path))
    receipts.record(tmp_path, "task-up", "up", "k", {"a": 1})
    receipts.finalize(tmp_path, "task-up", "up", "PR_OPEN")
    assert launcher._print_receipt(tmp_path, "up") == 0
    doc = json.loads(receipts.receipt_path(tmp_path, "task-up").read_text())
    doc["entries"]["k"] = {"a": 2}
    receipts.receipt_path(tmp_path, "task-up").write_text(json.dumps(doc))
    assert launcher._print_receipt(tmp_path, "up") == 1
    assert "digest mismatch" in capsys.readouterr().out


def harness_settings(tmp_path, port=8123, queue="factory-coordinator", extra=True,
                     worker=True, registry=True):
    root = tmp_path / "factory"
    src = root / "src" / "agent_factory" / "harness"
    src.mkdir(parents=True)
    if worker:
        (src / "worker.py").write_text("")
    extras = "[project.optional-dependencies]\nharness = ['temporal-agent-harness[ui]==0.11.0']\n"
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n" + (extras if extra else ""))
    path = root / "harness" / "agents.toml"
    path.parent.mkdir(parents=True)
    if registry:
        path.write_text("[[agents]]\nkey = 'factory-coordinator'\n")
    return launcher.HarnessSettings(registry=path, port=port, task_queue=queue,
                                    factory_root=root)


def test_harness_commands_name_registry_port_and_local_host(tmp_path):
    settings = harness_settings(tmp_path)
    command = launcher.harness_dev_command(settings)
    assert command[:6] == ["uv", "run", "--extra", "harness", "temporal-agent-harness", "dev"]
    assert command[6] == str(settings.registry)
    assert command[command.index("--port") + 1] == "8123"
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert launcher.coordinator_command() == [
        sys.executable, "-m", "agent_factory.harness.worker"]


def test_harness_env_sets_shared_temporal_queue_and_pythonpath(tmp_path):
    settings = harness_settings(tmp_path)
    base = {"PATH": "/bin", "TEMPORAL_NAMESPACE": "factory-ns", "TEMPORAL_TLS": "true"}
    env = launcher.harness_env(settings, "localhost:9999", base=base)
    assert env["TEMPORAL_ADDRESS"] == "localhost:9999"
    assert env["FACTORY_TEMPORAL_ADDRESS"] == "localhost:9999"
    assert env["FACTORY_HARNESS_TASK_QUEUE"] == "factory-coordinator"
    assert env["TEMPORAL_NAMESPACE"] == "factory-ns" and env["TEMPORAL_TLS"] == "true"
    assert env["PYTHONPATH"].split(":")[0] == str(settings.factory_root / "src")
    assert "TEMPORAL_ADDRESS" not in base, "caller env is not mutated"


def test_harness_preflight_is_precise_about_missing_parts(tmp_path, monkeypatch):
    settings = harness_settings(tmp_path, registry=False)
    assert "registry not found" in launcher.harness_preflight_reason(settings)

    settings = harness_settings(tmp_path / "no-extra", extra=False)
    assert "harness" in launcher.harness_preflight_reason(settings)

    settings = harness_settings(tmp_path / "no-worker", worker=False)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(launcher.importlib.util, "find_spec", lambda name: None)
    assert "coordinator package" in launcher.harness_preflight_reason(settings)

    settings = harness_settings(tmp_path / "ready")
    assert launcher.harness_preflight_reason(settings) is None
    monkeypatch.setattr(launcher.shutil, "which", lambda name: None)
    assert "uv" in launcher.harness_preflight_reason(settings)


def test_factory_queues_add_the_default_queue_only_for_harness(monkeypatch):
    from agent_factory.models import TaskSpec
    monkeypatch.setenv("FACTORY_TASK_QUEUE", "ops")
    spec = TaskSpec(**task(task_queue="per-task"))
    assert launcher._factory_queues([spec], harness=False) == ["per-task"]
    assert launcher._factory_queues([spec], harness=True) == ["ops", "per-task"]
    assert launcher._factory_queues([], harness=True) == ["ops"]


def test_startup_block_names_ports_queues_and_tasks(tmp_path):
    settings = harness_settings(tmp_path)
    block = launcher._startup_block(
        settings, "localhost:7233", True, ["factory", "ops"],
        [types.SimpleNamespace(id="task-a")], settings.factory_root / "state" / "harness")
    assert block.startswith("READY")
    assert "localhost:7233 (started)" in block
    assert "http://localhost:8233" in block
    assert "http://127.0.0.1:8123" in block
    assert "factory-coordinator" in block
    assert "factory, ops" in block and "task-a" in block
    assert launcher._temporal_ui("localhost:51549", started=True) == "http://localhost:52549"
    assert launcher._temporal_ui("temporal.example:7233", started=True) == ""


def test_up_needs_a_task_or_harness_and_harness_preflight_blocks_early(
        tmp_path, monkeypatch, capsys):
    args = types.SimpleNamespace(task=[], harness=False)
    assert asyncio.run(launcher.up(args)) == 2
    assert "nothing to run" in capsys.readouterr().err

    args = types.SimpleNamespace(task=[], harness=True, address="localhost:1",
                                 harness_registry=str(tmp_path / "missing.toml"),
                                 harness_port=8123)
    assert asyncio.run(launcher.up(args)) == 2
    assert "registry not found" in capsys.readouterr().err


def test_harness_stack_starts_harness_then_coordinator_and_stops_groups(tmp_path, monkeypatch):
    settings = harness_settings(tmp_path)
    spawned = []

    class FakePopen:
        def __init__(self, command, **kwargs):
            self.command, self.kwargs = command, kwargs
            self.pid = 4100 + len(spawned)
            self.returncode = None
            spawned.append(self)

        def poll(self):
            return None

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    monkeypatch.setattr(launcher.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(launcher, "_port_open", lambda port: False)
    monkeypatch.setattr(launcher, "HARNESS_STARTUP_GRACE_SECONDS", 0)

    async def api_ready(*args, **kwargs):
        return None

    monkeypatch.setattr(launcher, "_wait_for_api", api_ready)
    killed = []
    monkeypatch.setattr(launcher.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    stack = launcher.HarnessStack(settings, "localhost:9999", tmp_path / "state", ["factory"])
    asyncio.run(stack.start())

    assert [proc.command[0] for proc in spawned] == ["uv", sys.executable]
    assert spawned[0].command[5] == "dev"
    assert spawned[1].command[1:] == ["-m", "agent_factory.harness.worker"]
    assert spawned[0].kwargs["cwd"] == str(settings.factory_root)
    assert spawned[0].kwargs["env"]["TEMPORAL_ADDRESS"] == "localhost:9999"
    assert spawned[0].kwargs["env"]["FACTORY_HARNESS_TASK_QUEUE"] == "factory-coordinator"
    assert (tmp_path / "state" / "harness" / "harness.log").exists()
    assert (tmp_path / "state" / "harness" / "coordinator.log").exists()
    record = json.loads(launcher._record_path(tmp_path / "state").read_text())
    assert record["state"] == "running" and record["console_url"] == "http://127.0.0.1:8123"
    assert set(record["processes"]) == {"harness", "coordinator"}

    stack.stop()
    assert killed == [(spawned[1].pid, launcher.signal.SIGTERM),
                      (spawned[0].pid, launcher.signal.SIGTERM)]
    record = json.loads(launcher._record_path(tmp_path / "state").read_text())
    assert record["state"] == "stopped" and record["stopped_at"]


def test_harness_stack_refuses_a_busy_port(tmp_path, monkeypatch):
    settings = harness_settings(tmp_path)
    monkeypatch.setattr(launcher, "_port_open", lambda port: True)
    monkeypatch.setattr(launcher.subprocess, "Popen",
                        lambda *a, **k: pytest.fail("must not spawn"))
    with pytest.raises(launcher.HarnessError, match="already accepting"):
        asyncio.run(launcher.HarnessStack(
            settings, "localhost:9999", tmp_path / "state", ["factory"]).start())


def test_harness_stack_readiness_failure_stops_harness_and_records_error(tmp_path, monkeypatch):
    settings = harness_settings(tmp_path)
    spawned = []

    class FakePopen:
        def __init__(self, command, **kwargs):
            self.command, self.pid, self.returncode = command, 4200, None
            spawned.append(self)

        def poll(self):
            return None

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    monkeypatch.setattr(launcher.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(launcher, "_port_open", lambda port: False)

    async def never_ready(*args, **kwargs):
        raise launcher.HarnessError("harness API did not accept connections; log: harness.log")

    monkeypatch.setattr(launcher, "_wait_for_api", never_ready)
    killed = []
    monkeypatch.setattr(launcher.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(launcher.HarnessError, match="did not accept"):
        asyncio.run(launcher.HarnessStack(
            settings, "localhost:9999", tmp_path / "state", ["factory"]).start())
    assert len(spawned) == 1 and spawned[0].command[0] == "uv"
    assert killed == [(spawned[0].pid, launcher.signal.SIGTERM)]
    record = json.loads(launcher._record_path(tmp_path / "state").read_text())
    assert record["state"] == "failed" and "did not accept" in record["error"]


def test_wait_for_api_returns_once_the_port_accepts(tmp_path):
    class Alive:
        returncode = None

        def poll(self):
            return None

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        asyncio.run(launcher._wait_for_api(
            listener.getsockname()[1], Alive(), tmp_path / "harness.log", timeout=1))


def test_wait_for_api_detects_an_exited_process(tmp_path):
    class Dead:
        returncode = 1

        def poll(self):
            return 1

    with pytest.raises(launcher.HarnessError, match="exited before"):
        asyncio.run(launcher._wait_for_api(1, Dead(), tmp_path / "harness.log", timeout=1))


def test_harness_liveness_checks_recorded_port_and_processes(tmp_path, monkeypatch):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        record = {"schema": launcher.HARNESS_STACK_SCHEMA, "state": "running",
                  "port": port, "console_url": launcher._console_url(port),
                  "registry": "agents.toml", "coordinator_queue": "factory-coordinator",
                  "factory_queues": ["factory"], "processes": {"harness": 11, "coordinator": 12}}
        launcher._record_path(tmp_path).parent.mkdir(parents=True)
        launcher._record_path(tmp_path).write_text(json.dumps(record))
        monkeypatch.setattr(launcher, "_pid_alive", lambda pid: pid == 11)
        live = launcher.harness_liveness(tmp_path)
        assert live["listening"] is True and live["port"] == port
        assert live["state"] == "running"
        assert live["processes"]["harness"]["alive"] is True
        assert live["processes"]["coordinator"]["alive"] is False
        assert launcher.harness_liveness(tmp_path, port=port + 1)["listening"] is False


def test_status_without_tasks_reports_only_harness_liveness(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FACTORY_STATE_DIR", str(tmp_path))
    record = {"schema": launcher.HARNESS_STACK_SCHEMA, "state": "stopped", "port": 8000,
              "processes": {}, "coordinator_queue": "factory-coordinator"}
    launcher._record_path(tmp_path).parent.mkdir(parents=True)
    launcher._record_path(tmp_path).write_text(json.dumps(record))
    monkeypatch.setattr(launcher, "_port_open", lambda port: False)
    args = types.SimpleNamespace(address="localhost:1", harness_port=None, task_id=[])
    assert asyncio.run(launcher.status(args)) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["harness"]["state"] == "stopped" and row["harness"]["listening"] is False


def test_parser_allows_no_task_with_harness_and_repeatable_tasks():
    args = launcher._parser().parse_args(["up", "--harness"])
    assert args.task == [] and args.harness is True
    assert args.harness_port == 8000 and args.harness_registry is None
    args = launcher._parser().parse_args(["up", "--task", "a.json", "--task", "b.json"])
    assert args.task == ["a.json", "b.json"] and args.harness is False
