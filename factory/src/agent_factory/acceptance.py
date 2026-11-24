"""Read-only acceptance gates for the remote factory control plane.

This module does not deploy, restart, submit work, or call Railway, Temporal,
OpenCode or xPlan. Each track publishes observations into one evidence bundle;
the evaluator validates those observations and computes every gate.

Rules that keep the report honest:

- A missing observation is ``BLOCKED``, never ``PASS``.
- An observation that is present but contradicts the contract is ``FAIL``.
- A gate whose prerequisite is not ``PASS`` is reported ``BLOCKED`` even when
  its own fields look complete.
- Evidence files are optional but, when declared, are hashed. A missing file is
  ``BLOCKED``; a changed byte is ``FAIL``.
- Secret-shaped evidence is rejected before any gate is evaluated.

The bundle format and the gate contract are documented in
``factory/acceptance/README.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "agent-factory.remote-acceptance-bundle/1"
PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"
STATUSES = (PASS, FAIL, BLOCKED)

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")

PLACEHOLDERS = {"", "none", "null", "tbd", "todo", "n/a", "unavailable", "unknown"}
SECRET_KEYS = {
    "api_key", "apikey", "authorization", "password", "secret", "token",
    "temporal_api_key", "railway_token", "opencode_api_key", "xplan_token",
}
SECRET_VALUE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
PLANNER_DECISIONS = {
    "NO_CHANGE", "PROPOSE", "REWORK", "SKIP_CONFLICT", "STALE_SHA",
    "NEEDS_OWNER", "GATE_PENDING",
}


@dataclass(frozen=True)
class Gate:
    id: str
    title: str
    track: str
    depends_on: tuple[str, ...] = ()


GATES: tuple[Gate, ...] = (
    Gate("RAILWAY_FACTORY_DEPLOYED",
         "Railway project, environment and service are deployed at the tested SHA", "A6"),
    Gate("RAILWAY_OPENCODE_READY",
         "One remote OpenCode instance is authenticated and privately reachable", "A6",
         ("RAILWAY_FACTORY_DEPLOYED",)),
    Gate("TEMPORAL_POLLERS_ACTIVE",
         "factory-code, factory-coordinator and bsc-batch each have pollers", "A6/A2"),
    Gate("ITSPLAN_TASK_BINDING_PASS",
         "Issue binding and dry-run reconciliation are read-only and repeatable", "ITSPLAN",
         ("REMOTE_CODING_E2E_PASS",)),
    Gate("REMOTE_CODING_E2E_PASS",
         "A real remote OpenCode task passed tests and independent review", "remote-coding",
         ("RAILWAY_OPENCODE_READY", "TEMPORAL_POLLERS_ACTIVE",
          "REMOTE_FACTORY_READY")),
    Gate("EXTERNAL_BATCH_WORKER_PASS",
         "A BSC batch ran on external compute with no Railway bulk data", "A2/A3/A1",
         ("TEMPORAL_POLLERS_ACTIVE",)),
    Gate("RESTART_RECOVERY_PASS",
         "Railway and external worker restarts resumed with no duplicate effects", "A6/A2",
         ("REMOTE_CODING_E2E_PASS", "EXTERNAL_BATCH_WORKER_PASS")),
    Gate("MAC_INDEPENDENCE_PASS",
         "Local processes stopped while the remote workflow continued", "A6/A5",
         ("REMOTE_CODING_E2E_PASS", "EXTERNAL_BATCH_WORKER_PASS")),
    Gate("REMOTE_FACTORY_READY",
         "Remote factory worker, coordinator and private console are ready", "A6",
         ("RAILWAY_FACTORY_DEPLOYED", "TEMPORAL_POLLERS_ACTIVE",
          "RAILWAY_OPENCODE_READY")),
    Gate("REMOTE_OPENCODE_PASS",
         "A real remote OpenCode call succeeded with private access", "A6",
         ("RAILWAY_OPENCODE_READY",)),
    Gate("DETERMINISTIC_BATCH_PASS",
         "Two batch runs over the same manifest produced the same checkpoint", "A2",
         ("EXTERNAL_BATCH_WORKER_PASS",)),
    Gate("BSC_0029_CANARY_PASS",
         "The BSC-0029 canary completed on external compute with DQ passing", "A3/A2",
         ("EXTERNAL_BATCH_WORKER_PASS",)),
    Gate("CHECKPOINT_RESUME_PASS",
         "A killed batch worker reused its checkpoint without rerunning the unit", "A2",
         ("EXTERNAL_BATCH_WORKER_PASS",)),
    Gate("DQ_READBACK_PASS",
         "Independent DQ readback matched the expected JSON and report hash", "A3/A2",
         ("EXTERNAL_BATCH_WORKER_PASS",)),
    Gate("ZERO_DUPLICATE_EFFECTS",
         "Coding, batch and restart paths produced no duplicate effects", "A5",
         ("REMOTE_CODING_E2E_PASS", "EXTERNAL_BATCH_WORKER_PASS",
          "RESTART_RECOVERY_PASS")),
    Gate("TELEMETRY_VERIFIED",
         "Agent and review telemetry came from OpenCode JSON with real cost/tokens", "A4",
         ("REMOTE_CODING_E2E_PASS",)),
)

_CHECKERS: dict[str, Callable[[dict, "Context"], dict]] = {}


def _gate(gate_id: str):
    def register(function: Callable[[dict, "Context"], dict]):
        _CHECKERS[gate_id] = function
        return function
    return register


@dataclass
class Context:
    now: datetime
    max_age: timedelta
    verify_artifacts: bool
    bundle_dir: Path
    artifact_errors: dict[str, tuple[str, str]]


def _result(status: str, *reasons: str, **facts: Any) -> dict:
    return {"status": status, "reasons": [r for r in reasons if r], "facts": facts}


def _good(**facts: Any) -> dict:
    return _result(PASS, **facts)


def _bad(reason: str, **facts: Any) -> dict:
    return _result(FAIL, reason, **facts)


def _blocked(reason: str, **facts: Any) -> dict:
    return _result(BLOCKED, reason, **facts)


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in PLACEHOLDERS


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha(value: Any, digest: re.Pattern) -> bool:
    return isinstance(value, str) and bool(digest.fullmatch(value))


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh(context: Context, value: Any, label: str) -> str | None:
    parsed = _parse_time(value)
    if parsed is None:
        return f"{label} is not an ISO-8601 timestamp"
    if parsed > context.now + timedelta(minutes=5):
        return f"{label} is in the future"
    if context.now - parsed > context.max_age:
        return f"{label} is older than {int(context.max_age.total_seconds() // 60)} minutes"
    return None


def _missing(section: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if key not in section or section[key] is None
            or section[key] == ""]


def _artifact_problems(section: dict, context: Context) -> list[str]:
    refs = section.get("artifacts", [])
    if refs is None:
        return []
    if not isinstance(refs, list):
        return ["artifacts must be a list"]
    problems = []
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            problems.append("artifact reference is not a non-empty string")
            continue
        if not context.verify_artifacts:
            continue
        state, reason = context.artifact_errors.get(ref, ("missing", "not declared"))
        if state != "ok":
            problems.append(f"artifact {ref}: {reason}")
    return problems


def _section(bundle: dict, gate_id: str) -> dict | None:
    value = (bundle.get("checks") or {}).get(gate_id)
    return value if isinstance(value, dict) else None


def _poller_count(value: Any) -> int | None:
    if not isinstance(value, dict):
        return None
    count = value.get("poller_count")
    if _integer(count):
        return count
    for key in ("pollers", "identities"):
        items = value.get(key)
        if isinstance(items, list):
            return len(items)
    return None


def _identities(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    items = value.get("identities")
    if not isinstance(items, list):
        items = value.get("pollers")
    if not isinstance(items, list):
        return []
    return [item if isinstance(item, str) else str((item or {}).get("identity", ""))
            for item in items]


@_gate("RAILWAY_FACTORY_DEPLOYED")
def railway_factory_deployed(section: dict, context: Context) -> dict:
    missing = _missing(section, ("project_id", "environment_id", "services",
                                 "deployment", "health", "git_sha"))
    if missing:
        return _blocked("no Railway factory deployment evidence: missing "
                        + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    services = section["services"]
    if not isinstance(services, dict) or not services:
        return _bad("services must be a non-empty role-to-id map")
    bad_services = [role for role, value in services.items() if not _text(value)]
    if bad_services:
        return _bad("services have empty ids: " + ", ".join(sorted(bad_services)))
    deployment = section["deployment"]
    if not isinstance(deployment, dict):
        return _bad("deployment must be an object")
    for key in ("id", "sha", "status"):
        if not _text(deployment.get(key)):
            return _blocked(f"deployment.{key} is not observed")
    if not _sha(deployment["sha"], SHA40):
        return _bad("deployment.sha is not a full 40-hex commit")
    if deployment["sha"] != section["git_sha"]:
        return _bad("deployment.sha does not equal the tested git_sha")
    if deployment["status"] not in {"SUCCESS", "HEALTHY", "DEPLOYED"}:
        return _bad(f"deployment status is {deployment['status']!r}, not a healthy state")
    health = section["health"]
    if not isinstance(health, dict):
        return _bad("health must be an object")
    if health.get("status") != PASS:
        return _bad(f"health.status is {health.get('status')!r}, not PASS")
    stale = _fresh(context, health.get("checked_at"), "health.checked_at")
    if stale:
        return _blocked(stale)
    if section.get("public_exposure") is True:
        return _bad("the factory service is publicly exposed")
    access = section.get("access")
    if access not in (None, "private", "railway-private"):
        return _bad(f"access is {access!r}, not private")
    return _good(
        project=section["project_id"], environment=section["environment_id"],
        deployment=deployment["sha"], services=len(services),
    )


@_gate("RAILWAY_OPENCODE_READY")
def railway_opencode_ready(section: dict, context: Context) -> dict:
    missing = _missing(section, ("instances", "auth", "access", "health"))
    if missing:
        return _blocked("no remote OpenCode evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    instances = section["instances"]
    if not isinstance(instances, list):
        return _bad("instances must be a list")
    if not instances:
        return _bad("no remote OpenCode instance is running")
    if len(instances) != 1:
        return _bad(f"expected one remote OpenCode instance, found {len(instances)}")
    instance = instances[0]
    if not isinstance(instance, dict):
        return _bad("the OpenCode instance is not an object")
    if not _text(instance.get("id")):
        return _blocked("OpenCode instance id is not observed")
    if instance.get("placement") != "railway":
        return _bad("the OpenCode instance is not placed on Railway")
    if instance.get("status") not in {"ready", "READY", "online", "ONLINE"}:
        return _bad(f"OpenCode instance status is {instance.get('status')!r}")
    auth = section["auth"]
    if not isinstance(auth, dict):
        return _bad("auth must be an object")
    if auth.get("authenticated") is not True:
        return _bad("OpenCode is not authenticated")
    if not _text(auth.get("provider")) or not _text(auth.get("model")):
        return _blocked("OpenCode provider/model is not observed")
    access = section["access"]
    if not isinstance(access, dict):
        return _bad("access must be an object")
    if access.get("public_domain") is not False:
        return _bad("OpenCode must not have a public domain")
    if access.get("method") not in {"railway-private", "ssh-tunnel"}:
        return _bad("OpenCode access must be railway-private or an SSH tunnel")
    health = section["health"]
    if not isinstance(health, dict) or health.get("status") != PASS:
        return _bad("OpenCode health is not PASS")
    stale = _fresh(context, health.get("checked_at"), "health.checked_at")
    if stale:
        return _blocked(stale)
    return _good(instance=instance["id"], model=auth["model"])


@_gate("TEMPORAL_POLLERS_ACTIVE")
def temporal_pollers_active(section: dict, context: Context) -> dict:
    missing = _missing(section, ("target", "namespace", "observed_at", "queues"))
    if missing:
        return _blocked("no Temporal poller evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    stale = _fresh(context, section["observed_at"], "observed_at")
    if stale:
        return _blocked(stale)

    queues = section["queues"]
    if not isinstance(queues, dict):
        return _bad("queues must be an object")
    required = ("factory-code", "factory-coordinator", "bsc-batch")
    absent = [name for name in required if name not in queues]
    if absent:
        return _blocked("queues not observed: " + ", ".join(absent))
    observed: dict[str, dict] = {}
    empty: list[str] = []
    for name in required:
        entry = queues[name]
        if not isinstance(entry, dict):
            return _bad(f"queue {name} is not an object")
        workflow = _poller_count(entry.get("workflow"))
        activity = _poller_count(entry.get("activity"))
        if workflow is None or activity is None:
            return _blocked(f"queue {name} has no poller counts")
        identities = _identities(entry.get("workflow")) + _identities(entry.get("activity"))
        observed[name] = {"workflow": workflow, "activity": activity,
                          "identities": [i for i in identities if i]}
        if workflow == 0 and activity == 0:
            empty.append(name)
        elif workflow < 1 or activity < 1:
            return _bad(f"queue {name} is missing workflow or activity pollers")
        elif not observed[name]["identities"]:
            return _bad(f"queue {name} reports pollers without an identity")

    placements = section.get("placement") or {}
    if placements and not isinstance(placements, dict):
        return _bad("placement must be an object")
    expected = {"factory-code": "railway", "factory-coordinator": "railway",
                "bsc-batch": "external-compute"}
    for name, wanted in expected.items():
        actual = placements.get(name)
        if actual is not None and actual != wanted:
            return _bad(f"queue {name} is placed on {actual!r}, expected {wanted!r}")

    if len(empty) == len(required):
        return _blocked("0 pollers on factory-code, factory-coordinator and bsc-batch")
    if empty:
        return _bad("queues without pollers: " + ", ".join(empty))
    return _good(target=section["target"], pollers=observed)


@_gate("ITSPLAN_TASK_BINDING_PASS")
def itsplan_task_binding(section: dict, context: Context) -> dict:
    missing = _missing(section, ("issue", "binding", "planner", "write_audit", "replay"))
    if missing:
        return _blocked("no xPlan binding evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    issue = section["issue"]
    binding = section["binding"]
    planner = section["planner"]
    audit = section["write_audit"]
    replay = section["replay"]
    for name, value in (("issue", issue), ("binding", binding), ("planner", planner),
                        ("write_audit", audit), ("replay", replay)):
        if not isinstance(value, dict):
            return _bad(f"{name} must be an object")

    if not _text(issue.get("identifier")):
        return _blocked("issue.identifier is not observed")
    if not _integer(issue.get("id")):
        return _blocked("issue.id is not observed")
    for key in ("updatedAt", "columnId"):
        if key not in issue:
            return _blocked(f"issue.{key} is not observed")
    if not _text(issue.get("observed_revision")):
        return _blocked("issue.observed_revision is not observed")
    if issue.get("source_revision") != issue.get("observed_revision"):
        return _bad("the issue changed between binding and readback")

    bound = binding.get("issue")
    if not isinstance(bound, dict):
        return _blocked("binding.issue is not observed")
    if (bound.get("id"), bound.get("identifier")) != (issue.get("id"), issue.get("identifier")):
        return _bad("readback does not match the bound issue")
    if not _text(binding.get("run_id")) or not _text(binding.get("worker")):
        return _blocked("binding.run_id or binding.worker is not observed")
    columns = binding.get("columns")
    if not isinstance(columns, dict) or not isinstance(columns.get("IN_PROGRESS"), int):
        return _blocked("binding.columns has no numeric IN_PROGRESS column")

    if planner.get("mode") != "dry_run":
        return _bad("xPlan planner did not report dry_run mode")
    if planner.get("decision") not in PLANNER_DECISIONS:
        return _bad("xPlan planner decision is unknown")
    if planner.get("decision") == "PROPOSE" and not _integer(planner.get("proposed_column_id")):
        return _bad("a PROPOSE decision must name an integer proposed column")
    if planner.get("decision") != "PROPOSE" and planner.get("proposed_column_id") is not None:
        return _bad("a non-PROPOSE dry-run must not propose a column")

    if audit.get("writes_attempted") != 0 or audit.get("writes_applied") != 0:
        return _bad("the planner access attempted or applied a mutation")
    methods = audit.get("methods")
    if not isinstance(methods, list) or any(method not in {"GET", "HEAD", "OPTIONS"}
                                           for method in methods):
        return _bad("the planner access used a non-read-only HTTP method")
    paths = audit.get("paths")
    if not isinstance(paths, list) or paths:
        return _bad("the planner access recorded a mutation path")

    if replay.get("identical") is not True:
        return _bad("the dry-run replay was not identical")
    if replay.get("decision") != planner.get("decision"):
        return _bad("the replay decision differs from the first dry-run")
    return _good(issue=issue["identifier"], decision=planner["decision"],
                 writes=0, run_id=binding["run_id"])


@_gate("REMOTE_CODING_E2E_PASS")
def remote_coding_e2e(section: dict, context: Context) -> dict:
    missing = _missing(section, ("task_id", "workflow_id", "workflow_status", "execution",
                                 "agent", "tests", "review", "checkpoints", "pr",
                                 "receipt", "duplicates"))
    if missing:
        return _blocked("no remote coding evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    if not _text(section["task_id"]):
        return _blocked("task_id is not observed")
    if section["workflow_id"] != f"task-{section['task_id']}":
        return _bad("workflow_id does not match task-<task_id>")
    if section["workflow_status"] != "PR_OPEN":
        return _bad(f"workflow status is {section['workflow_status']!r}, not PR_OPEN")
    execution = section["execution"]
    if not isinstance(execution, dict):
        return _bad("execution must be an object")
    if execution.get("placement") != "railway":
        return _bad("the coding task did not execute on Railway")
    if execution.get("local_process") is not False:
        return _bad("the coding task used a local process")
    agent = section["agent"]
    if not isinstance(agent, dict):
        return _bad("agent must be an object")
    if agent.get("runner") != "opencode":
        return _bad("the coding task did not run through OpenCode")
    if not _text(agent.get("model")):
        return _blocked("agent model is not observed")
    if not _integer(agent.get("steps")) or agent["steps"] < 1:
        return _bad("agent.steps must be a positive integer")
    if not _text(agent.get("session_id")):
        return _blocked("agent session_id is not observed")
    tests = section["tests"]
    if not isinstance(tests, dict) or tests.get("passed") is not True:
        return _bad("tests did not pass")
    review = section["review"]
    if not isinstance(review, dict):
        return _bad("review must be an object")
    if review.get("verdict") != "APPROVE":
        return _bad("independent review did not approve")
    if review.get("independent") is not True:
        return _bad("review is not marked independent")
    if review.get("session_id") == agent["session_id"]:
        return _bad("review reused the implementation session")
    if not _sha(review.get("diff_sha256"), SHA64):
        return _bad("review has no reviewed diff hash")
    if not _sha(review.get("prompt_sha256"), SHA64):
        return _bad("review has no reviewed prompt hash")
    checkpoints = section["checkpoints"]
    if not isinstance(checkpoints, list) or not checkpoints:
        return _bad("no checkpoint commits are recorded")
    shas = []
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict) or not _sha(checkpoint.get("sha"), SHA40):
            return _bad("a checkpoint SHA is not a full 40-hex commit")
        shas.append(checkpoint["sha"])
    if len(set(shas)) != len(shas):
        return _bad("checkpoint commits are duplicated")
    pr = section["pr"]
    if not isinstance(pr, dict):
        return _bad("pr must be an object")
    if not _integer(pr.get("number")) or pr["number"] < 1:
        return _bad("PR number is not observed")
    if pr.get("head_sha") != shas[-1]:
        return _bad("PR head is not the last checkpoint")
    receipt = section["receipt"]
    if not isinstance(receipt, dict) or not _sha(receipt.get("sha256"), SHA64):
        return _bad("receipt has no SHA-256")
    duplicates = section["duplicates"]
    if not isinstance(duplicates, dict):
        return _bad("duplicates must be an object")
    if duplicates.get("commits") != 0 or duplicates.get("prs") != 0:
        return _bad("coding path produced duplicate commits or PRs")
    return _good(task=section["task_id"], pr=pr["number"], checkpoints=len(shas),
                 review=review.get("model"))


@_gate("EXTERNAL_BATCH_WORKER_PASS")
def external_batch_worker(section: dict, context: Context) -> dict:
    missing = _missing(section, ("job_id", "workflow_id", "task_queue", "status",
                                 "worker", "units", "data_plane", "receipt"))
    if missing:
        return _blocked("no external batch evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    if not _text(section["job_id"]):
        return _blocked("job_id is not observed")
    if section["workflow_id"] != f"batch-{section['job_id']}":
        return _bad("workflow_id does not match batch-<job_id>")
    if section["task_queue"] != "bsc-batch":
        return _bad("the batch did not use the bsc-batch queue")
    if section["status"] != "BATCH_SUCCESS":
        return _bad(f"batch status is {section['status']!r}, not BATCH_SUCCESS")
    worker = section["worker"]
    if not isinstance(worker, dict):
        return _bad("worker must be an object")
    if worker.get("placement") not in {"external", "external-compute"}:
        return _bad("the batch worker is not on external compute")
    if _text(worker.get("railway_service_id")):
        return _bad("the batch worker is a Railway service")
    if not _text(worker.get("identity")):
        return _blocked("batch worker identity is not observed")
    units = section["units"]
    if not isinstance(units, list) or not units:
        return _bad("the batch has no units")
    outputs = 0
    for unit in units:
        if not isinstance(unit, dict):
            return _bad("a batch unit is not an object")
        if unit.get("status") not in {"COMPLETED", "REUSED"}:
            return _bad(f"unit {unit.get('unit_id')!r} is not completed")
        if unit.get("status") == "COMPLETED" and unit.get("exit_code") != 0:
            return _bad(f"unit {unit.get('unit_id')!r} exited nonzero")
        if isinstance(unit.get("outputs"), dict):
            outputs += len(unit["outputs"])
    if outputs == 0:
        return _bad("the batch declared no outputs")
    data = section["data_plane"]
    if not isinstance(data, dict):
        return _bad("data_plane must be an object")
    if data.get("bulk_data_on_railway") is not False:
        return _bad("bulk batch data is on Railway")
    if not _integer(data.get("railway_bytes")) or data["railway_bytes"] > 1_048_576:
        return _bad("Railway received more than 1 MiB of batch data")
    if data.get("durable_state_placement") not in {"external", "external-compute"}:
        return _bad("batch checkpoints are not on external durable storage")
    receipt = section["receipt"]
    if not isinstance(receipt, dict) or not _sha(receipt.get("sha256"), SHA64):
        return _bad("batch receipt has no SHA-256")
    return _good(job=section["job_id"], units=len(units), worker=worker["identity"],
                 railway_bytes=data["railway_bytes"])


@_gate("RESTART_RECOVERY_PASS")
def restart_recovery(section: dict, context: Context) -> dict:
    missing = _missing(section, ("railway_restart", "external_restart", "recovery",
                                 "duplicates", "continuity"))
    if missing:
        return _blocked("no restart evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    railway = section["railway_restart"]
    external = section["external_restart"]
    for name, value in (("railway_restart", railway), ("external_restart", external)):
        if not isinstance(value, dict):
            return _bad(f"{name} must be an object")
    if not _text(railway.get("service_id")):
        return _blocked("railway_restart.service_id is not observed")
    if not _integer(railway.get("restart_count")) or railway["restart_count"] < 1:
        return _bad("the Railway service was not restarted")
    stale = _fresh(context, railway.get("observed_at"), "railway_restart.observed_at")
    if stale:
        return _blocked(stale)
    if not _text(external.get("worker_identity")):
        return _blocked("external_restart.worker_identity is not observed")
    if not _integer(external.get("restart_count")) or external["restart_count"] < 1:
        return _bad("the external worker was not restarted")
    stale = _fresh(context, external.get("observed_at"), "external_restart.observed_at")
    if stale:
        return _blocked(stale)

    recovery = section["recovery"]
    if not isinstance(recovery, dict):
        return _bad("recovery must be an object")
    if recovery.get("resumed") is not True:
        return _bad("the workflow did not resume after restart")
    if recovery.get("replay") != "PASS":
        return _bad("Temporal history replay did not pass")
    if not _text(recovery.get("terminal_state")):
        return _blocked("recovery.terminal_state is not observed")
    if not _integer(recovery.get("checkpoints_reused")) or recovery["checkpoints_reused"] < 1:
        return _bad("no checkpoint was reused after restart")

    duplicates = section["duplicates"]
    if not isinstance(duplicates, dict):
        return _bad("duplicates must be an object")
    for key in ("commits", "prs", "batch_units", "side_effects"):
        if duplicates.get(key) != 0:
            return _bad(f"restart produced duplicate {key}")
    continuity = section["continuity"]
    if not isinstance(continuity, dict):
        return _bad("continuity must be an object")
    before, after = continuity.get("before_sha"), continuity.get("after_sha")
    if not _sha(before, SHA40) or not _sha(after, SHA40):
        return _bad("continuity SHAs are not full 40-hex commits")
    if before != after:
        return _bad("restart changed the workflow head SHA")
    return _good(railway_restarts=railway["restart_count"],
                 external_restarts=external["restart_count"],
                 reused=recovery["checkpoints_reused"])


@_gate("MAC_INDEPENDENCE_PASS")
def mac_independence(section: dict, context: Context) -> dict:
    missing = _missing(section, ("local", "remote"))
    if missing:
        return _blocked("no Mac independence evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    local = section["local"]
    remote = section["remote"]
    if not isinstance(local, dict) or not isinstance(remote, dict):
        return _bad("local and remote must be objects")
    stale = _fresh(context, local.get("stopped_at"), "local.stopped_at")
    if stale:
        return _blocked(stale)
    processes = local.get("processes")
    if not isinstance(processes, list) or not processes:
        return _bad("no stopped local processes are recorded")
    for process in processes:
        if not isinstance(process, dict) or not _text(process.get("name")):
            return _bad("a local process record has no name")
        if process.get("running_after") is not False:
            return _bad(f"local process {process.get('name')!r} was still running")
    ports = local.get("ports")
    if not isinstance(ports, list) or not ports:
        return _bad("no local ports are recorded")
    for port in ports:
        if not isinstance(port, dict) or not _integer(port.get("port")):
            return _bad("a local port record is invalid")
        if port.get("listening_after") is not False:
            return _bad(f"local port {port['port']} was still listening")
    if local.get("remote_tunnels_required") is not False:
        return _bad("remote execution still requires a local tunnel")

    if remote.get("continued") is not True:
        return _bad("the remote workflow did not continue")
    if remote.get("observed_after_local_stop") is not True:
        return _bad("remote progress was not observed after local shutdown")
    if not _text(remote.get("workflow_id")):
        return _blocked("remote.workflow_id is not observed")
    if not _text(remote.get("terminal_state")):
        return _blocked("remote.terminal_state is not observed")
    return _good(workflow=remote["workflow_id"], state=remote["terminal_state"],
                 stopped=local["stopped_at"])


@_gate("REMOTE_FACTORY_READY")
def remote_factory_ready(section: dict, context: Context) -> dict:
    missing = _missing(section, ("release_sha", "services", "state"))
    if missing:
        return _blocked("no remote factory readiness evidence: missing "
                        + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    if not _sha(section["release_sha"], SHA40):
        return _bad("release_sha is not a full 40-hex commit")

    services = section["services"]
    if not isinstance(services, dict):
        return _bad("services must be an object")
    for role, queue in (("factory_worker", "factory-code"),
                        ("coordinator", "factory-coordinator")):
        service = services.get(role)
        if not isinstance(service, dict):
            return _blocked(f"services.{role} is not observed")
        if service.get("status") not in {"online", "ONLINE", "running", "RUNNING"}:
            return _bad(f"services.{role} is not online")
        if service.get("queue") != queue:
            return _bad(f"services.{role} does not poll {queue}")
    console = services.get("console")
    if not isinstance(console, dict):
        return _blocked("services.console is not observed")
    if console.get("status") not in {"online", "ONLINE", "running", "RUNNING"}:
        return _bad("the remote console is not online")
    if console.get("private") is not True:
        return _bad("the remote console is not private")
    state = section["state"]
    if not isinstance(state, dict):
        return _bad("state must be an object")
    if state.get("durable") is not True:
        return _bad("remote factory state is not durable")
    if state.get("receipts_readable") is not True:
        return _bad("remote receipts are not readable")
    return _good(release=section["release_sha"])


@_gate("REMOTE_OPENCODE_PASS")
def remote_opencode(section: dict, context: Context) -> dict:
    missing = _missing(section, ("instance", "auth", "real_call", "access"))
    if missing:
        return _blocked("no remote OpenCode call evidence: missing "
                        + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))

    instance = section["instance"]
    if not isinstance(instance, dict):
        return _bad("instance must be an object")
    if instance.get("placement") != "railway":
        return _bad("the OpenCode instance is not on Railway")
    auth = section["auth"]
    if not isinstance(auth, dict) or auth.get("authenticated") is not True:
        return _bad("the remote OpenCode instance is not authenticated")
    model = auth.get("model")
    if not _text(model):
        return _blocked("the remote OpenCode model is not observed")
    if isinstance(model, str) and model.endswith("-free"):
        return _bad("a free model is not accepted for private code")
    call = section["real_call"]
    if not isinstance(call, dict):
        return _bad("real_call must be an object")
    if call.get("exit_code") != 0:
        return _bad("the real remote OpenCode call exited nonzero")
    if not _text(call.get("session_id")):
        return _blocked("the real call has no OpenCode session id")
    if not _sha(call.get("text_sha256"), SHA64):
        return _bad("the real call has no response hash")
    access = section["access"]
    if not isinstance(access, dict):
        return _bad("access must be an object")
    if access.get("public_domain") is not False:
        return _bad("the remote OpenCode instance is publicly reachable")
    return _good(model=model, session=call["session_id"])


@_gate("DETERMINISTIC_BATCH_PASS")
def deterministic_batch(section: dict, context: Context) -> dict:
    missing = _missing(section, ("job_id", "manifest_hash", "script_sha", "runs",
                                 "checkpoint_fields"))
    if missing:
        return _blocked("no deterministic batch evidence: missing "
                        + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    if not _sha(section["manifest_hash"], SHA64):
        return _bad("manifest_hash is not a SHA-256")
    if not _sha(section["script_sha"], SHA64):
        return _bad("script_sha is not a SHA-256")
    fields = section["checkpoint_fields"]
    if not isinstance(fields, list):
        return _bad("checkpoint_fields must be a list")
    forbidden = {"timestamp", "created_at", "finished_at", "duration", "seconds",
                 "path", "absolute_path", "run_id"}
    if forbidden.intersection({str(field).lower() for field in fields}):
        return _bad("the checkpoint contains non-deterministic fields")
    runs = section["runs"]
    if not isinstance(runs, list) or len(runs) < 2:
        return _bad("at least two runs are required")
    first = runs[0]
    if not isinstance(first, dict):
        return _bad("a run is not an object")
    for key in ("checkpoint_digest",):
        if not _sha(first.get(key), SHA64):
            return _bad(f"run 0 has no {key}")
    first_outputs = first.get("outputs")
    if not isinstance(first_outputs, dict) or not first_outputs:
        return _bad("run 0 has no outputs")
    for index, run in enumerate(runs[1:], start=1):
        if not isinstance(run, dict):
            return _bad(f"run {index} is not an object")
        if run.get("checkpoint_digest") != first["checkpoint_digest"]:
            return _bad(f"run {index} has a different checkpoint digest")
        if run.get("outputs") != first_outputs:
            return _bad(f"run {index} has different output hashes")
    if section.get("deterministic") is not True:
        return _bad("the evidence did not assert determinism")
    return _good(job=section["job_id"], runs=len(runs),
                 checkpoint=first["checkpoint_digest"])


@_gate("BSC_0029_CANARY_PASS")
def bsc_0029_canary(section: dict, context: Context) -> dict:
    missing = _missing(section, ("job_id", "status", "worker", "dq", "outputs",
                                 "receipt", "canary"))
    if missing:
        return _blocked("no BSC-0029 evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    if str(section["job_id"]).lower() != "bsc-0029":
        return _bad("the evidence is not for the BSC-0029 canary")
    if section["status"] != "BATCH_SUCCESS":
        return _bad(f"canary status is {section['status']!r}, not BATCH_SUCCESS")
    if section.get("canary") is not True:
        return _bad("the canary marker is missing")
    worker = section["worker"]
    if not isinstance(worker, dict) or worker.get("placement") not in {
            "external", "external-compute"}:
        return _bad("the canary did not run on external compute")
    dq = section["dq"]
    if not isinstance(dq, dict) or dq.get("status") != PASS:
        return _bad("the canary DQ contract did not pass")
    outputs = section["outputs"]
    if not isinstance(outputs, dict) or not outputs:
        return _bad("the canary declared no outputs")
    receipt = section["receipt"]
    if not isinstance(receipt, dict) or not _sha(receipt.get("sha256"), SHA64):
        return _bad("the canary receipt has no SHA-256")
    return _good(job="bsc-0029", units=len(outputs))


@_gate("CHECKPOINT_RESUME_PASS")
def checkpoint_resume(section: dict, context: Context) -> dict:
    missing = _missing(section, ("job_id", "unit_id", "killed", "worker_restart",
                                 "resume", "counts", "receipt"))
    if missing:
        return _blocked("no checkpoint resume evidence: missing "
                        + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    if section.get("killed") is not True:
        return _bad("the worker was not killed during the unit")
    restart = section["worker_restart"]
    if not isinstance(restart, dict) or restart.get("observed") is not True:
        return _bad("the replacement worker was not observed")
    resume = section["resume"]
    if not isinstance(resume, dict):
        return _bad("resume must be an object")
    if resume.get("checkpoint_reused") is not True:
        return _bad("the checkpoint was not reused")
    if resume.get("unit_rerun") is not False:
        return _bad("the unit was rerun after resume")
    if resume.get("outputs_match") is not True:
        return _bad("resumed outputs do not match")
    counts = section["counts"]
    if not isinstance(counts, dict) or counts.get("unit_executions") != 1:
        return _bad("the unit executed more than once")
    receipt = section["receipt"]
    if not isinstance(receipt, dict) or not _sha(receipt.get("sha256"), SHA64):
        return _bad("the resume receipt has no SHA-256")
    return _good(job=section["job_id"], unit=section["unit_id"],
                 executions=counts["unit_executions"])


@_gate("DQ_READBACK_PASS")
def dq_readback(section: dict, context: Context) -> dict:
    missing = _missing(section, ("job_id", "dq", "readback"))
    if missing:
        return _blocked("no DQ readback evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    dq = section["dq"]
    if not isinstance(dq, dict):
        return _bad("dq must be an object")
    if dq.get("status") != PASS:
        return _bad("DQ status is not PASS")
    if dq.get("exit_code") != dq.get("expected_exit"):
        return _bad("DQ exit code does not match the contract")
    if not _sha(dq.get("report_sha256"), SHA64):
        return _bad("DQ report has no SHA-256")
    if not isinstance(dq.get("expected_json"), dict) or not isinstance(
            dq.get("reported_json"), dict):
        return _blocked("DQ expected/reported JSON is not observed")
    if dq["expected_json"] != dq["reported_json"]:
        return _bad("DQ reported JSON differs from the expected JSON")
    readback = section["readback"]
    if not isinstance(readback, dict):
        return _bad("readback must be an object")
    if readback.get("independent") is not True:
        return _bad("DQ readback is not independent")
    if readback.get("matches_expected") is not True:
        return _bad("independent readback did not match")
    if readback.get("report_hash_matches") is not True:
        return _bad("independent readback did not match the report hash")
    return _good(job=section["job_id"], report=dq["report_sha256"])


@_gate("ZERO_DUPLICATE_EFFECTS")
def zero_duplicate_effects(section: dict, context: Context) -> dict:
    missing = _missing(section, ("counts", "scope", "evidence", "independent"))
    if missing:
        return _blocked("no duplicate-effects evidence: missing "
                        + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    counts = section["counts"]
    if not isinstance(counts, dict):
        return _bad("counts must be an object")
    required = ("commits", "prs", "branches", "batch_units", "dq_reports",
                "receipts", "notifications")
    absent = [key for key in required if key not in counts]
    if absent:
        return _blocked("duplicate counters not observed: " + ", ".join(absent))
    for key in required:
        if not _integer(counts[key]):
            return _bad(f"duplicate counter {key} is not an integer")
        if counts[key] != 0:
            return _bad(f"duplicate {key} count is {counts[key]}")
    scope = section["scope"]
    if not isinstance(scope, list) or not {"coding", "batch", "restart"}.issubset(scope):
        return _bad("duplicate scope must cover coding, batch and restart")
    evidence = section["evidence"]
    if not isinstance(evidence, dict):
        return _bad("evidence must be an object")
    for name in ("coding", "batch", "restart"):
        if not _text(evidence.get(name)):
            return _blocked(f"no duplicate evidence for {name}")
    if section["independent"] is not True:
        return _bad("duplicate scan is not independent")
    return _good(counts=0, scope=scope)


@_gate("TELEMETRY_VERIFIED")
def telemetry_verified(section: dict, context: Context) -> dict:
    missing = _missing(section, ("schema", "source", "runs", "receipt"))
    if missing:
        return _blocked("no telemetry evidence: missing " + ", ".join(missing))
    problems = _artifact_problems(section, context)
    if problems:
        return _blocked("; ".join(problems))
    if section["schema"] != "agent-factory.opencode-telemetry/1":
        return _bad("telemetry schema is unknown")
    if section["source"] != "opencode-run-json":
        return _bad("telemetry did not come from OpenCode JSON output")
    runs = section["runs"]
    if not isinstance(runs, list) or not runs:
        return _bad("no telemetry runs are recorded")
    stages = set()
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            return _bad(f"run {index} is not an object")
        stage = run.get("stage")
        if stage not in {"agent", "review"}:
            return _bad(f"run {index} has an unknown stage {stage!r}")
        stages.add(stage)
        if not _text(run.get("model")) or not _text(run.get("session_id")):
            return _blocked(f"run {index} has no model/session id")
        if not _integer(run.get("steps")) or run["steps"] < 1:
            return _bad(f"run {index} has no measured steps")
        for key in ("cost", "input_tokens", "output_tokens"):
            if run.get(key) == "UNAVAILABLE":
                return _bad(f"run {index} {key} is UNAVAILABLE")
            if not _number(run.get(key)) or run[key] < 0:
                return _bad(f"run {index} {key} is not a non-negative number")
        if not _number(run.get("duration_seconds")) or run["duration_seconds"] <= 0:
            return _bad(f"run {index} has no measured duration")
        if run.get("exit_code") != 0:
            return _bad(f"run {index} did not exit zero")
        if not _sha(run.get("text_sha256"), SHA64):
            return _bad(f"run {index} has no response hash")
    if "review" not in stages:
        return _bad("no review telemetry run is recorded")
    if "agent" not in stages:
        return _bad("no agent-step telemetry run is recorded")
    receipt = section["receipt"]
    if not isinstance(receipt, dict):
        return _blocked("receipt evidence is not observed")
    if receipt.get("contains_telemetry") is not True:
        return _bad("the receipt does not carry telemetry")
    if not _sha(receipt.get("metrics_sha256"), SHA64):
        return _bad("the receipt telemetry digest is missing")
    total_cost = sum(float(run["cost"]) for run in runs)
    return _good(runs=len(runs), stages=sorted(stages), cost=round(total_cost, 6))


def _validate_envelope(bundle: dict) -> list[str]:
    if not isinstance(bundle, dict):
        return ["bundle must be a JSON object"]
    problems = []
    if bundle.get("schema") != SCHEMA:
        problems.append(f"schema must be {SCHEMA}")
    if _parse_time(bundle.get("generated_at")) is None:
        problems.append("generated_at must be an ISO-8601 timestamp")
    if bundle.get("commit") is not None and not _sha(bundle.get("commit"), SHA40):
        problems.append("commit must be a full 40-hex SHA when present")
    if not isinstance(bundle.get("checks"), dict):
        problems.append("checks must be an object")
    if bundle.get("artifacts") is not None and not isinstance(bundle["artifacts"], list):
        problems.append("artifacts must be a list")
    return problems


def _secret_problems(value: Any, path: str = "") -> list[str]:
    problems = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            here = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in SECRET_KEYS and isinstance(item, str) \
                    and item.strip() and item.lower() != "redacted":
                problems.append(f"secret-shaped value at {here}")
            problems.extend(_secret_problems(item, here))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            problems.extend(_secret_problems(item, f"{path}[{index}]"))
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        problems.append(f"secret-shaped value at {path or '<root>'}")
    return problems


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_states(bundle: dict, base: Path, verify: bool) -> dict[str, tuple[str, str]]:
    states: dict[str, tuple[str, str]] = {}
    for index, artifact in enumerate(bundle.get("artifacts") or []):
        if not isinstance(artifact, dict):
            states[f"invalid-{index}"] = ("missing", "artifact is not an object")
            continue
        artifact_id = artifact.get("id")
        if not _text(artifact_id):
            states[f"invalid-{index}"] = ("missing", "artifact has no id")
            continue
        path = artifact.get("path")
        expected = artifact.get("sha256")
        if not _text(path) or not _sha(expected, SHA64):
            states[artifact_id] = ("missing", "artifact has no path/SHA-256")
            continue
        if not verify:
            states[artifact_id] = ("ok", "not verified")
            continue
        target = Path(path)
        if not target.is_absolute():
            target = base / target
        if not target.is_file():
            states[artifact_id] = ("missing", "file not found")
            continue
        actual = _hash_file(target)
        if actual != expected:
            states[artifact_id] = ("changed", "sha256 mismatch")
        else:
            states[artifact_id] = ("ok", "verified")
    return states


def evaluate(bundle: dict, *, now: datetime | None = None,
             max_age_hours: float = 24, verify_artifacts: bool = True,
             bundle_dir: Path | None = None) -> dict:
    """Evaluate every gate. Raises ValueError for an invalid evidence envelope."""
    problems = _validate_envelope(bundle)
    problems.extend(_secret_problems(bundle))
    if problems:
        raise ValueError("; ".join(problems))
    current = now or datetime.now(timezone.utc)
    base = bundle_dir or Path.cwd()
    context = Context(
        now=current,
        max_age=timedelta(hours=max_age_hours),
        verify_artifacts=verify_artifacts,
        bundle_dir=base,
        artifact_errors=_artifact_states(bundle, base, verify_artifacts),
    )

    direct: dict[str, dict] = {}
    for gate in GATES:
        section = _section(bundle, gate.id)
        if section is None:
            direct[gate.id] = _blocked("no evidence section for this gate")
        else:
            direct[gate.id] = _CHECKERS[gate.id](section, context)

    by_id = {gate.id: gate for gate in GATES}
    results: dict[str, dict] = {}

    def resolve(gate_id: str) -> dict:
        if gate_id in results:
            return results[gate_id]
        gate = by_id[gate_id]
        result = dict(direct[gate_id])
        if result["status"] == PASS and gate.depends_on:
            blocked = []
            for dependency in gate.depends_on:
                dependency_result = resolve(dependency)
                if dependency_result["status"] != PASS:
                    blocked.append(f"{dependency}={dependency_result['status']}")
            if blocked:
                result = _blocked("prerequisite not passing: " + ", ".join(blocked))
        results[gate_id] = {
            "id": gate.id,
            "title": gate.title,
            "track": gate.track,
            "depends_on": list(gate.depends_on),
            **result,
        }
        return results[gate_id]

    for gate in GATES:
        resolve(gate.id)
    ordered = {gate.id: results[gate.id] for gate in GATES}
    results = ordered

    passed = sum(1 for result in results.values() if result["status"] == PASS)
    if any(result["status"] == FAIL for result in results.values()):
        overall = FAIL
    elif any(result["status"] == BLOCKED for result in results.values()):
        overall = BLOCKED
    else:
        overall = PASS
    return {
        "schema": "agent-factory.remote-acceptance-report/1",
        "bundle_schema": SCHEMA,
        "generated_at": bundle["generated_at"],
        "commit": bundle.get("commit"),
        "environment": bundle.get("environment"),
        "overall": overall,
        "passed": passed,
        "total": len(GATES),
        "gates": results,
    }


def report_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def report_markdown(report: dict) -> str:
    lines = [
        "# Remote factory acceptance",
        "",
        f"- Bundle schema: `{report['bundle_schema']}`",
        f"- Evidence generated: `{report['generated_at']}`",
        f"- Source commit: `{report['commit'] or 'not recorded'}`",
        f"- Environment: `{report['environment'] or 'not recorded'}`",
        f"- Overall: **{report['overall']}** ({report['passed']}/{report['total']} gates)",
        "",
        "| Gate | Track | Status | Evidence or blocker |",
        "|---|---|---|---|",
    ]
    for gate in report["gates"].values():
        reason = "; ".join(gate["reasons"]) if gate["reasons"] else "observed"
        reason = reason.replace("|", "\\|")
        if len(reason) > 500:
            reason = reason[:497] + "..."
        lines.append(f"| `{gate['id']}` | {gate['track']} | **{gate['status']}** | {reason} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agent_factory.acceptance",
        description="Validate one remote-factory acceptance evidence bundle.",
    )
    parser.add_argument("--bundle", required=True, type=Path,
                        help="path to the evidence JSON")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, default=None,
                        help="write the report to this path as well as stdout")
    parser.add_argument("--max-age-hours", type=float, default=24.0,
                        help="maximum age for live observations (default 24)")
    parser.add_argument("--no-artifacts", action="store_true",
                        help="do not hash artifact files (inspection only)")
    args = parser.parse_args(argv)

    try:
        bundle = json.loads(args.bundle.read_text())
    except (OSError, ValueError) as exc:
        print(f"acceptance: cannot read bundle: {exc}", file=sys.stderr)
        return 2
    try:
        report = evaluate(bundle, max_age_hours=args.max_age_hours,
                          verify_artifacts=not args.no_artifacts,
                          bundle_dir=args.bundle.resolve().parent)
    except ValueError as exc:
        print(f"acceptance: invalid bundle: {exc}", file=sys.stderr)
        return 2

    text = report_markdown(report) if args.format == "markdown" else report_json(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        os.chmod(args.output, 0o600)
    print(text, end="" if text.endswith("\n") else "\n")
    if report["overall"] == PASS:
        return 0
    if report["overall"] == FAIL:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["GATES", "SCHEMA", "evaluate", "main", "report_json", "report_markdown"]
