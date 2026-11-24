"""Durable per-unit checkpoints.

Path: `FACTORY_STATE_DIR/checkpoints/<job_id>/<unit_id>.json`. Writes are
atomic and locked. A checkpoint is reused only after read-back proves all of:

- schema and digest are intact;
- `job_id`, `unit_id`, `manifest_hash`, `script_sha`, `unit_fingerprint` and
  `inputs_hash` equal the current spec/unit fence;
- every declared output exists and its bytes still match the recorded SHA-256.

The digest contains no timestamps, durations or absolute state paths, so the
same manifest over the same outputs produces the same checkpoint digest.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .manifest import inputs_hash, unit_fingerprint
from .models import (CHECKPOINT_SCHEMA, BatchJobSpec, BatchUnit, Checkpoint,
                     CheckpointState)
from .util import sha256_file, sha256_json

TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class CheckpointError(ValueError):
    """A checkpoint or one of its outputs cannot be trusted."""


def checkpoint_path(state_dir: Path | str, job_id: str, unit_id: str) -> Path:
    # Re-validate here too: these values become path components.
    if not TOKEN_RE.fullmatch(job_id) or not TOKEN_RE.fullmatch(unit_id):
        raise CheckpointError("job_id and unit_id must be path-safe tokens")
    return Path(state_dir) / "checkpoints" / job_id / f"{unit_id}.json"


@contextmanager
def _locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _atomic_write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(document, indent=2, sort_keys=True) + "\n"
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def checkpoint_body(checkpoint: Checkpoint) -> dict:
    """The digest content: deterministic fields only, no path or duration."""
    return {
        "schema": checkpoint.schema,
        "job_id": checkpoint.job_id,
        "unit_id": checkpoint.unit_id,
        "manifest_hash": checkpoint.manifest_hash,
        "script_sha": checkpoint.script_sha,
        "unit_fingerprint": checkpoint.unit_fingerprint,
        "inputs_hash": checkpoint.inputs_hash,
        "outputs": dict(sorted(checkpoint.outputs.items())),
        "status": checkpoint.status,
    }


def checkpoint_digest(checkpoint: Checkpoint) -> str:
    return sha256_json(checkpoint_body(checkpoint))


def output_hashes(workspace: Path | str, outputs: list[str]) -> dict[str, str]:
    """Hash every declared output; missing/non-file outputs are an error."""
    root = Path(workspace).resolve()
    result: dict[str, str] = {}
    for rel in outputs:
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise CheckpointError(f"output escapes the workspace: {rel}") from exc
        if not path.is_file():
            raise CheckpointError(f"declared output is missing or not a file: {rel}")
        result[rel] = sha256_file(path)
    return result


def build_checkpoint(spec: BatchJobSpec, unit: BatchUnit,
                     outputs: dict[str, str]) -> Checkpoint:
    checkpoint = Checkpoint(
        job_id=spec.job_id,
        unit_id=unit.unit_id,
        manifest_hash=spec.manifest_hash,
        script_sha=spec.script_sha,
        unit_fingerprint=unit.fingerprint or unit_fingerprint(unit),
        inputs_hash=inputs_hash(unit.inputs),
        outputs=dict(sorted(outputs.items())),
    )
    checkpoint.digest = checkpoint_digest(checkpoint)
    return checkpoint


def write_checkpoint(state_dir: Path | str, spec: BatchJobSpec,
                     unit: BatchUnit) -> Checkpoint:
    """Hash the declared outputs and atomically store the completed unit."""
    checkpoint = build_checkpoint(spec, unit, output_hashes(spec.workspace, unit.outputs))
    path = checkpoint_path(state_dir, spec.job_id, unit.unit_id)
    document = {**checkpoint_body(checkpoint), "digest": checkpoint.digest}
    with _locked(path):
        _atomic_write(path, document)
    checkpoint.path = str(path)
    return checkpoint


def _decode(document: dict, path: Path) -> Checkpoint:
    required = ("schema", "job_id", "unit_id", "manifest_hash", "script_sha",
                "unit_fingerprint", "inputs_hash", "outputs", "status", "digest")
    missing = [key for key in required if key not in document]
    if missing:
        raise CheckpointError(f"checkpoint missing keys: {missing}")
    if document["schema"] != CHECKPOINT_SCHEMA:
        raise CheckpointError("checkpoint schema is unknown")
    checkpoint = Checkpoint(
        job_id=str(document["job_id"]),
        unit_id=str(document["unit_id"]),
        manifest_hash=str(document["manifest_hash"]),
        script_sha=str(document["script_sha"]),
        unit_fingerprint=str(document["unit_fingerprint"]),
        inputs_hash=str(document["inputs_hash"]),
        outputs={str(key): str(value) for key, value in dict(document["outputs"]).items()},
        status=str(document["status"]),
        schema=str(document["schema"]),
        digest=str(document["digest"]),
        path=str(path),
    )
    if checkpoint_digest(checkpoint) != checkpoint.digest:
        raise CheckpointError("checkpoint digest mismatch")
    return checkpoint


def read_checkpoint(state_dir: Path | str, spec: BatchJobSpec,
                    unit: BatchUnit) -> CheckpointState:
    """Read and fence one checkpoint. Never guesses: each rejection names its reason."""
    path = checkpoint_path(state_dir, spec.job_id, unit.unit_id)
    if not path.exists():
        return CheckpointState(valid=False, reason="missing")
    try:
        document = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return CheckpointState(valid=False, reason=f"unreadable: {exc}")
    if not isinstance(document, dict):
        return CheckpointState(valid=False, reason="not-an-object")
    try:
        checkpoint = _decode(document, path)
    except CheckpointError as exc:
        return CheckpointState(valid=False, reason=str(exc))

    fence = {
        "job_id": (checkpoint.job_id, spec.job_id),
        "unit_id": (checkpoint.unit_id, unit.unit_id),
        "manifest_hash": (checkpoint.manifest_hash, spec.manifest_hash),
        "script_sha": (checkpoint.script_sha, spec.script_sha),
        "unit_fingerprint": (checkpoint.unit_fingerprint,
                             unit.fingerprint or unit_fingerprint(unit)),
        "inputs_hash": (checkpoint.inputs_hash, inputs_hash(unit.inputs)),
    }
    for name, (recorded, current) in fence.items():
        if recorded != current:
            return CheckpointState(valid=False, reason=f"fence-mismatch:{name}",
                                   checkpoint=checkpoint)
    if set(checkpoint.outputs) != set(unit.outputs):
        return CheckpointState(valid=False, reason="output-set-mismatch",
                               checkpoint=checkpoint)
    try:
        actual = output_hashes(spec.workspace, unit.outputs)
    except CheckpointError as exc:
        return CheckpointState(valid=False, reason=str(exc), checkpoint=checkpoint)
    for rel, recorded in checkpoint.outputs.items():
        if actual.get(rel) != recorded:
            return CheckpointState(valid=False, reason=f"output-mismatch:{rel}",
                                   checkpoint=checkpoint)
    return CheckpointState(valid=True, reason="valid", checkpoint=checkpoint)


def load_document(path: Path | str) -> Optional[dict]:
    """Raw checkpoint document, for operator inspection and tests."""
    source = Path(path)
    if not source.exists():
        return None
    document = json.loads(source.read_text())
    return document if isinstance(document, dict) else None


__all__ = [
    "CheckpointError", "build_checkpoint", "checkpoint_body", "checkpoint_digest",
    "checkpoint_path", "load_document", "output_hashes", "read_checkpoint",
    "write_checkpoint",
]
