"""Propose one xPlan transition from read-only snapshots and delivery evidence."""

from __future__ import annotations

import json
from pathlib import Path
import re

import click


def plan_transition(binding: dict, observed: dict, event: dict) -> dict:
    """Compare a pinned issue and SHA with the current observations."""
    pinned = binding["issue"]
    columns = binding["columns"]
    for issue in (pinned, observed):
        if not issue["updatedAt"] or type(issue["columnId"]) is not int:
            raise ValueError("an observed issue needs updatedAt and a numeric columnId")
    if any(observed[key] != pinned[key] for key in ("id", "identifier")):
        raise ValueError("readback does not match the bound issue")
    git_sha = event["git_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", git_sha):
        raise ValueError("git_sha must be a full commit SHA")
    current = observed["columnId"]
    refs = event.get("evidence_refs", [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError("evidence_refs must contain nonempty reference strings")

    receipt = {
        "issue_id": pinned["identifier"],
        "source_revision": pinned["updatedAt"],
        "observed_revision": observed["updatedAt"],
        "git_sha": git_sha,
        "run_id": binding["run_id"],
        "current_column_id": current,
        "proposed_column_id": None,
        "proposed_status": None,
        "worker": None,
        "reason": None,
        "evidence_refs": refs,
        "mode": "dry_run",
    }

    def result(decision: str, reason: str, status: str | None = None,
               column: int | None = None, worker: str | None = None) -> dict:
        return {**receipt, "decision": decision, "reason": reason, "proposed_status": status,
                "proposed_column_id": column, "worker": worker}

    if (observed["updatedAt"], current) != (pinned["updatedAt"], pinned["columnId"]):
        return result("SKIP_CONFLICT", "issue changed after the binding was captured")
    if current not in columns.values():
        raise ValueError("current column is missing from the xPlan column map")

    kind = event["kind"]
    review = event.get("review") or {}
    if kind in {"rework", "accepted"} and review.get("git_sha") not in (None, git_sha):
        return result("STALE_SHA", "review does not cover the current Git revision")

    if kind in {"worker_finished", "tests_passed"}:
        return result("NO_CHANGE", "worker and test receipts do not satisfy the delivery gate")
    if kind == "needs_owner":
        if not event.get("question"):
            raise ValueError("needs_owner requires a specific question")
        return result("NEEDS_OWNER", event["question"], "NEEDS_OWNER")
    if kind == "rework":
        findings = review.get("findings")
        if not findings or not binding.get("worker") or review.get("git_sha") != git_sha:
            raise ValueError("rework requires review findings and a bound worker")
        return result("REWORK", findings, "REWORK", worker=binding["worker"])
    if kind == "started":
        status = "IN_PROGRESS"
    elif kind == "accepted":
        required = binding["required_delivery_level"]
        verified = event.get("verified_delivery_level")
        if type(required) is not int or required not in range(1, 7):
            raise ValueError("required_delivery_level must be 1 through 6")
        if (type(verified) is not int or not required <= verified <= 6
                or review.get("git_sha") != git_sha or review.get("verdict") != "ACCEPT"
                or not review.get("evidence_ref")
                or not receipt["evidence_refs"]):
            return result("GATE_PENDING", "required evidence or review is missing")
        status = "DONE"
    else:
        raise ValueError(f"unknown lifecycle event: {kind}")

    target = columns[status]
    if current == target:
        return result("NO_CHANGE", "the issue is already in the proposed column")
    if current in (columns["DONE"], columns.get("CANCELED")):
        return result("GATE_PENDING", "a terminal issue requires an explicit reopen")
    return result("PROPOSE", kind, status, target)


@click.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli(input_file: Path) -> None:
    """Print a dry-run decision from a binding, observed issue, and event JSON."""
    try:
        data = json.loads(input_file.read_text())
        receipt = plan_transition(data["binding"], data["observed"], data["event"])
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    cli()
