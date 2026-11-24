"""Offline batch contract tests: freeze, paths, checkpoints, runners, limits.

No Temporal server and no model. Workflow behaviour is covered separately in
`test_batch_workflow.py`.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from agent_factory.batch import checkpoints, runner
from agent_factory.batch.manifest import (BatchManifestError, compute_manifest_hash,
                                          inputs_hash, load_job_spec, parse_manifest,
                                          unit_fingerprint)
from agent_factory.batch.models import ResourceLimits

SOURCE = Path(__file__).resolve().parents[1] / "src" / "agent_factory" / "batch"


def _script(tmp_path: Path, runner_id: str, body: str) -> tuple[Path, str]:
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)
    name = {"python": "job.py", "bash": "job.sh", "rust": "job"}[runner_id]
    path = workspace / name
    path.write_text(body)
    if runner_id in {"bash", "rust"}:
        path.chmod(0o755)
    return workspace, name


def make_manifest(tmp_path: Path, *, runner_id: str = "python", body: str | None = None,
                  units: list[dict] | None = None, dq: dict | None = None,
                  env: dict | None = None, args: list | None = None,
                  script: str | None = None, workspace: Path | None = None,
                  hash_value: str | None = None) -> tuple[Path, dict, Path]:
    default_body = {
        "python": "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('ok')\n",
        "bash": "printf ok > \"$1\"\n",
        "rust": "#!/bin/sh\nprintf ok > \"$1\"\n",
    }[runner_id]
    ws, name = _script(tmp_path, runner_id, body if body is not None else default_body)
    units = units if units is not None else [{"unit_id": "u1", "outputs": ["out/u1.txt"]}]
    data = {
        "job_id": "job-1",
        "runner_id": runner_id,
        "workspace": str(workspace or ws),
        "script": script if script is not None else name,
        "script_sha": checkpoints.sha256_file(ws / name),
        "units": units,
    }
    if env is not None:
        data["env"] = env
    if args is not None:
        data["args"] = args
    if dq is not None:
        data["dq_contract"] = dq
    data["manifest_hash"] = compute_manifest_hash(data) if hash_value is None else hash_value
    path = tmp_path / "job.json"
    path.write_text(json.dumps(data))
    return path, data, ws


def rewrite(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def test_manifest_hash_and_script_sha_are_frozen(tmp_path):
    path, data, ws = make_manifest(tmp_path)
    spec = load_job_spec(path)
    assert spec.job_id == "job-1" and spec.units[0].unit_id == "u1"
    assert spec.manifest_hash == data["manifest_hash"]

    data["job_id"] = "job-2"
    rewrite(path, data)
    with pytest.raises(BatchManifestError, match="manifest_hash mismatch"):
        load_job_spec(path)

    path, data, ws = make_manifest(tmp_path / "second")
    (ws / "job.py").write_text("print('tampered')\n")
    with pytest.raises(BatchManifestError, match="script_sha mismatch"):
        load_job_spec(path)


def test_manifest_must_declare_its_hash_and_known_keys(tmp_path):
    path, data, _ = make_manifest(tmp_path)
    broken = dict(data)
    broken.pop("manifest_hash")
    rewrite(path, broken)
    with pytest.raises(BatchManifestError, match="manifest_hash is required"):
        load_job_spec(path)

    path, data, _ = make_manifest(tmp_path / "unknown")
    data["shell"] = "bash -c evil"
    data["manifest_hash"] = compute_manifest_hash(data)
    rewrite(path, data)
    with pytest.raises(BatchManifestError, match="unknown keys"):
        load_job_spec(path)


@pytest.mark.parametrize("script", ["../escape.py", "/etc/passwd", "a/../../x.py"])
def test_script_paths_cannot_escape_the_workspace(tmp_path, script):
    path, data, _ = make_manifest(tmp_path, script=script)
    with pytest.raises(BatchManifestError):
        load_job_spec(path)


def test_symlinked_script_cannot_escape_the_workspace(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("print('evil')\n")
    path, data, ws = make_manifest(tmp_path)
    (ws / "link.py").symlink_to(outside)
    data["script"] = "link.py"
    data["script_sha"] = checkpoints.sha256_file(outside)
    data["manifest_hash"] = compute_manifest_hash(data)
    rewrite(path, data)
    with pytest.raises(BatchManifestError, match="escapes the workspace"):
        load_job_spec(path)


@pytest.mark.parametrize("key,value", [
    ("outputs", ["../out.txt"]),
    ("outputs", ["/tmp/out.txt"]),
    ("inputs", {"../input.txt": None}),
])
def test_unit_paths_cannot_escape_the_workspace(tmp_path, key, value):
    unit = {"unit_id": "u1", key: value}
    path, _data, _ws = make_manifest(tmp_path, units=[unit])
    with pytest.raises(BatchManifestError):
        load_job_spec(path)


def test_unapproved_env_and_absolute_args_are_rejected(tmp_path):
    path, _data, _ws = make_manifest(tmp_path, env={"LD_PRELOAD": "/tmp/x.so"})
    with pytest.raises(BatchManifestError, match="allowlist"):
        load_job_spec(path)

    path, _data, _ws = make_manifest(tmp_path / "factory", env={"FACTORY_STATE_DIR": "/tmp"})
    with pytest.raises(BatchManifestError, match="allowlist"):
        load_job_spec(path)

    path, _data, _ws = make_manifest(tmp_path / "abs", args=["--input=/etc/passwd"])
    with pytest.raises(BatchManifestError, match="absolute paths"):
        load_job_spec(path)

    path, _data, _ws = make_manifest(tmp_path / "rel", args=["--input=../secret"])
    with pytest.raises(BatchManifestError, match="traversal"):
        load_job_spec(path)

    path, _data, _ws = make_manifest(tmp_path / "ok", env={"PYTHONHASHSEED": "0"},
                                     args=["--shard", "0"])
    spec = load_job_spec(path)
    assert spec.env == {"PYTHONHASHSEED": "0"} and spec.args == ["--shard", "0"]


def test_duplicate_unit_ids_and_output_collisions_are_rejected(tmp_path):
    same_id = [{"unit_id": "u1", "outputs": ["a"]}, {"unit_id": "u1", "outputs": ["b"]}]
    path, _data, _ws = make_manifest(tmp_path, units=same_id)
    with pytest.raises(BatchManifestError, match="duplicate unit id"):
        load_job_spec(path)

    same_output = [{"unit_id": "u1", "outputs": ["same.txt"]},
                   {"unit_id": "u2", "outputs": ["same.txt"]}]
    path, _data, _ws = make_manifest(tmp_path / "out", units=same_output)
    with pytest.raises(BatchManifestError, match="already declared"):
        load_job_spec(path)

    identical = [{"outputs": ["a"]}, {"outputs": ["a"]}]  # derived ids collide
    path, _data, _ws = make_manifest(tmp_path / "derived", units=identical)
    with pytest.raises(BatchManifestError, match="duplicate unit id"):
        load_job_spec(path)


def test_derived_unit_ids_are_stable_and_content_bound(tmp_path):
    units = [{"outputs": ["a"]}, {"outputs": ["b"]}]
    path, _data, _ws = make_manifest(tmp_path, units=units)
    first = load_job_spec(path)
    second = load_job_spec(path)
    assert [u.unit_id for u in first.units] == [u.unit_id for u in second.units]
    assert first.units[0].unit_id.startswith("u-")
    assert first.units[0].fingerprint == unit_fingerprint(first.units[0])
    path2, _data2, _ws2 = make_manifest(
        tmp_path / "other", units=[{"outputs": ["a"], "resource_limits": {"timeout_seconds": 9}}])
    changed = load_job_spec(path2)
    assert changed.units[0].unit_id != first.units[0].unit_id


def test_checkpoint_write_is_atomic_and_fenced(tmp_path):
    state = tmp_path / "state"
    path, _data, ws = make_manifest(tmp_path)
    spec = load_job_spec(path)
    unit = spec.units[0]
    unit.checkpoint = str(checkpoints.checkpoint_path(state, spec.job_id, unit.unit_id))
    (ws / "out").mkdir()
    (ws / "out" / "u1.txt").write_text("result")

    checkpoint = checkpoints.write_checkpoint(state, spec, unit)
    file = checkpoints.checkpoint_path(state, spec.job_id, unit.unit_id)
    assert file.is_file() and checkpoint.digest
    assert not list(file.parent.glob("*.tmp.*"))
    assert checkpoints.read_checkpoint(state, spec, unit).valid

    document = json.loads(file.read_text())
    document["outputs"]["out/u1.txt"] = "0" * 64
    file.write_text(json.dumps(document))
    state_view = checkpoints.read_checkpoint(state, spec, unit)
    assert not state_view.valid and "digest" in state_view.reason

    # Restore a valid checkpoint, then change the manifest fence.
    checkpoints.write_checkpoint(state, spec, unit)
    spec.manifest_hash = "f" * 64
    state_view = checkpoints.read_checkpoint(state, spec, unit)
    assert not state_view.valid and state_view.reason == "fence-mismatch:manifest_hash"

    spec.manifest_hash = checkpoint.manifest_hash
    spec.script_sha = "e" * 64
    state_view = checkpoints.read_checkpoint(state, spec, unit)
    assert state_view.reason == "fence-mismatch:script_sha"

    spec.script_sha = checkpoint.script_sha
    unit.inputs = {"different.txt": None}
    state_view = checkpoints.read_checkpoint(state, spec, unit)
    assert state_view.reason.startswith("fence-mismatch:")
    unit.inputs = {}

    (ws / "out" / "u1.txt").unlink()
    state_view = checkpoints.read_checkpoint(state, spec, unit)
    assert not state_view.valid and "missing" in state_view.reason

    (ws / "out" / "u1.txt").write_text("changed")
    state_view = checkpoints.read_checkpoint(state, spec, unit)
    assert not state_view.valid and state_view.reason.startswith("output-mismatch")


def test_checkpoint_digest_is_deterministic_across_state_dirs(tmp_path):
    path, _data, ws = make_manifest(tmp_path)
    spec = load_job_spec(path)
    unit = spec.units[0]
    (ws / "out").mkdir()
    (ws / "out" / "u1.txt").write_text("same")
    one = checkpoints.write_checkpoint(tmp_path / "state-a", spec, unit)
    two = checkpoints.write_checkpoint(tmp_path / "state-b", spec, unit)
    assert one.digest == two.digest
    assert one.path != two.path


def test_checkpoint_requires_pinned_input_bytes(tmp_path):
    inputs = {"in.txt": None}
    path, data, ws = make_manifest(tmp_path, units=[
        {"unit_id": "u1", "inputs": inputs, "outputs": ["out/u1.txt"]}])
    (ws / "in.txt").write_text("one")
    data["units"][0]["inputs"] = {"in.txt": checkpoints.sha256_file(ws / "in.txt")}
    data["manifest_hash"] = compute_manifest_hash(data)
    rewrite(path, data)
    spec = load_job_spec(path)
    from agent_factory.batch.manifest import verify_inputs
    verify_inputs(spec, spec.units[0])
    (ws / "in.txt").write_text("two")
    with pytest.raises(BatchManifestError, match="input sha256 mismatch"):
        verify_inputs(spec, spec.units[0])
    assert inputs_hash({"in.txt": None}) == inputs_hash({"in.txt": None})


@pytest.mark.asyncio
@pytest.mark.parametrize("runner_id,body", [
    ("python", "import pathlib\npathlib.Path('ok.txt').write_text('python')\n"),
    ("bash", "printf bash > ok.txt\n"),
    ("rust", "#!/bin/sh\nprintf rust > ok.txt\n"),
])
async def test_allowlisted_runners_execute_without_a_shell(tmp_path, runner_id, body):
    ws, name = _script(tmp_path, runner_id, body)
    log = tmp_path / "run.log"
    outcome = await runner.run_limited(
        runner.runner_argv(runner_id, ws / name, []), ws,
        {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}, log,
        ResourceLimits(timeout_seconds=20, cpu_seconds=20, memory_mb=1024,
                       output_bytes=100000),
        lambda _proc: None)
    assert outcome.exit_code == 0
    assert (ws / "ok.txt").read_text().strip() == runner_id


@pytest.mark.asyncio
async def test_unknown_runner_is_rejected():
    with pytest.raises(runner.BatchRunError, match="unknown batch runner"):
        runner.runner_argv("shell", Path("/bin/sh"), [])


@pytest.mark.asyncio
async def test_output_cap_kills_a_runaway_writer(tmp_path):
    ws, name = _script(tmp_path, "python", "import sys\nsys.stdout.write('x' * 200000)\n")
    with pytest.raises(runner.BatchRunError) as caught:
        await runner.run_limited(
            runner.runner_argv("python", ws / name, []), ws,
            {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}, tmp_path / "cap.log",
            ResourceLimits(timeout_seconds=20, cpu_seconds=20, memory_mb=1024,
                           output_bytes=1024),
            lambda _proc: None)
    assert caught.value.kind == "output"


@pytest.mark.asyncio
async def test_wall_timeout_kills_the_process_group(tmp_path):
    ws, name = _script(tmp_path, "python", "import time\ntime.sleep(30)\n")
    with pytest.raises(runner.BatchRunError) as caught:
        await runner.run_limited(
            runner.runner_argv("python", ws / name, []), ws,
            {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}, tmp_path / "time.log",
            ResourceLimits(timeout_seconds=1, cpu_seconds=10, memory_mb=1024,
                           output_bytes=100000),
            lambda _proc: None)
    assert caught.value.kind == "timeout"


def test_batch_source_uses_no_shell_and_no_model_provider():
    denylisted = {"openai", "anthropic", "google", "litellm", "agents", "strands", "cohere"}
    for path in sorted(SOURCE.glob("*.py")):
        text = path.read_text()
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert not any(keyword.arg == "shell" for keyword in node.keywords), path.name
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
        assert imported.isdisjoint(denylisted), (path.name, imported & denylisted)


def test_manifest_parser_is_pure_json(tmp_path):
    """No process is started while validating a manifest."""
    path, _data, _ws = make_manifest(tmp_path)
    spec = parse_manifest(json.loads(path.read_text()), manifest_path=str(path))
    assert spec.units[0].checkpoint == ""
