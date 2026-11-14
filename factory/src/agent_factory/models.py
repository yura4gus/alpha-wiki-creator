"""Serializable inputs and results shared by activities and the workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskSpec:
    task_id: str
    repo: str  # git URL or path used as origin; checkpoints are pushed here
    agent_steps: list[list[str]]  # argv per step; native CLI loops stay intact
    test_command: list[str]
    owned_paths: list[str]  # repo-relative prefixes this task may change
    base_ref: str = "main"
    context_files: list[str] = field(default_factory=list)
    env_passthrough: list[str] = field(default_factory=list)  # names only, never values
    task_queue: str = "factory"
    max_step_seconds: int = 900  # per-attempt budget for one agent step
    max_attempts: int = 2  # bounded retry for agent steps
    heartbeat_timeout_seconds: int = 30  # worker lease: no heartbeat -> reschedule
    test_timeout_seconds: int = 600
    require_approval: bool = True
    approval_timeout_seconds: int = 86400
    reviewer: str = "stub"  # stub | opencode
    review_model: str = "opencode/deepseek-v4.1-flash-free"  # provider/model for reviewer=opencode
    pr_backend: str = "local"  # local | gh
    pr_repo: Optional[str] = None  # owner/name, required for gh
    pr_title: str = ""
    xplan: Optional[dict] = None  # {"binding": ..., "observed": ...}; dry-run only
    plugin_root: Optional[str] = None  # checkout holding tools/xplan_dry_run.py


@dataclass
class Pinned:
    base_sha: str


@dataclass
class ContextResult:
    text: str
    sources: list[dict]


@dataclass
class StepResult:
    index: int
    sha: str
    changed: bool
    reused: bool
    exit_code: int
    log_tail: str
    seconds: float


@dataclass
class TestResult:
    passed: bool
    exit_code: int
    log_tail: str
    seconds: float


@dataclass
class ReviewRequest:
    base_sha: str
    head_sha: str
    context_text: str
    tests_passed: bool
    tests_tail: str


@dataclass
class ReviewResult:
    verdict: str  # APPROVE | CHANGES | BLOCKED
    findings: str
    reviewer: str
    head_sha: str


@dataclass
class Decision:
    verdict: str  # approve | reject
    by: str
    note: str = ""


@dataclass
class PRRequest:
    head_sha: str
    review_summary: str


@dataclass
class TaskResult:
    status: str
    base_sha: str = ""
    head_sha: str = ""
    pr: Optional[dict] = None
    review: Optional[dict] = None
    receipt_path: str = ""
    receipt_digest: str = ""
    error: str = ""
