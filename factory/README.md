# Agent Factory V1 (Temporal)

Optional package. The Alpha-Wiki plugin itself stays server-free; this directory has its
own `pyproject.toml` and environment, so no plugin manifest changes.

Responsibilities: **Temporal** owns durable execution, retries and approvals; **xPlan**
keeps task ownership (read-only dry-run here); **Alpha-Wiki** supplies context and
contracts; **OpenCode/Codex** run unchanged as subprocesses.

## Flow (`workflows.TaskWorkflow`, id `task-<task_id>`)
`pin_snapshot` → `build_context` → `agent_step`×N (each ends as one pushed checkpoint
commit on `factory/<task_id>`) → `run_tests` → `review` → human approval (Update
`decide`) → `open_pr` → `reconcile_dry_run` → receipt.

## Recovery model
- Worker filesystem is **ephemeral**; origin branch `factory/<task_id>` and the receipt
  in `FACTORY_STATE_DIR` are the durable record.
- A lost worker is detected by heartbeat timeout; the retried `agent_step` rebuilds the
  worktree from the last checkpoint SHA. A step already pushed is reused, not re-run
  (`Factory-Step: <task>/<index>` trailer).
- Commits are deterministic (parent, tree, message, base commit date), PRs are looked up
  by head branch, receipts are keyed per step: repeating any activity adds nothing.

## Run
```bash
cd factory && uv sync --python 3.12
temporal server start-dev                       # local Temporal
FACTORY_TASK_QUEUE=factory uv run python -m agent_factory.worker
uv run python -m agent_factory.client start task.json
uv run python -m agent_factory.client status <task_id>
uv run python -m agent_factory.client decide <task_id> approve --by <name>
uv run python -m agent_factory.client cancel <task_id>
uv run pytest                                   # needs /opt/homebrew/bin/temporal
```
`task.json` holds a `TaskSpec` (`models.py`). Example agent step for a real CLI:
`["opencode", "run", "<prompt>"]`; the context file path is in `FACTORY_CONTEXT_FILE`.
Pass credentials by listing variable **names** in `env_passthrough`; values stay in
the worker environment and never enter workflow history.

## Config (env)
`FACTORY_HOME`, `FACTORY_WORK_ROOT` (ephemeral), `FACTORY_STATE_DIR` (durable),
`FACTORY_TEMPORAL_ADDRESS`, `FACTORY_TASK_QUEUE`, `FACTORY_PLUGIN_ROOT`,
reviewer: `DEEPSEEK_API_KEY`, `FACTORY_REVIEW_MODEL`, `FACTORY_REVIEW_BASE_URL`.

## Not covered in V1
Real DeepSeek review (adapter written, not run: no credentials), real `gh` PRs
(adapter written, not run), live OpenCode/Codex runs, cmux, xPlan writes,
Continue-As-New for very long tasks, multi-host task queues.
