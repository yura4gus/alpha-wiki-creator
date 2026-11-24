# OpenCode telemetry and single-server contract

Status: parser, reviewer hook and offline tests are complete. A real bounded
coding task plus independent DeepSeek review passed on the Railway pilot
`agent-factory-runtime` in `agent-factory-control` / `pilot`; receipt:
`factory/receipts/remote-opencode-telemetry-20261125.json`. Gate:
`REMOTE_CODING_AND_REVIEW_PASS`. The earlier `the external compute host` free-model fallback is
superseded and was not the selected production server.

## Parser

`factory/src/agent_factory/telemetry.py` reads the JSON stream already produced by
`opencode run --format json`. It makes no provider request and knows no prices.

- `parse_opencode_telemetry(text)` → one summary.
- `parse_opencode_log(path)` → the same summary from a captured step/review log.
- `parse_run(text, model=..., wall_seconds=..., exit_code=..., stage=...)` → adds
  stage, exit code, wall duration and session id for one bounded CLI call.
- `final_text(text)` / `extract_text(text)` → recover the reviewer's answer from
  JSON text parts without treating tool output as the verdict.

Fields: `input_tokens`, `output_tokens`, `reasoning_tokens`,
`cache_read_tokens`, `cache_write_tokens`, `total_tokens`, `cost`, `steps`,
`models`, `model`, `sessions`, `session_id`, `source`, `missing`.

A field OpenCode did not report is the string `UNAVAILABLE`, never zero. Zero is
preserved because it is a real value for an empty cache or a provider-reported
zero cost. Aggregates are only computed when every contributing step supplies the
component. `step_finish` parts take precedence over assistant-message records so
the same model call is not counted twice.

`cost` is exactly what OpenCode reported. A paid provider that does not publish
pricing can report `0.0`; that is a reported value, not evidence that the model
was free. Free-model policy remains a separate admission check.

## Exact integration hooks

The telemetry parser is intentionally not wired into the frozen execution files.
The two hooks are:

1. **Step telemetry** — `factory/src/agent_factory/activities.py`,
   `agent_step`, after `run_command` and before `return StepResult(...)`:

   ```python
   usage = telemetry.parse_opencode_log(log)
   ```

   `parse_run` can add `wall_seconds` and `exit_code`; leave `model` unset unless
   the task spec or argv carries it, in which case `model` is reported as
   `UNAVAILABLE` rather than guessed.

   `StepResult` (`models.py`) needs a `usage: dict` field, and
   `workflows.py` needs to put it in the existing step metrics:

   ```python
   {"seconds": ..., "reused": ..., "exit_code": ..., "telemetry": step.usage}
   ```

   Equivalent without changing `models.py`: add one `record_step` activity call
   from the workflow with the same `usage` JSON.

2. **Review telemetry** — already implemented in `reviewer.py`. Pass a dict:

   ```python
   usage = {}
   result = reviewer.opencode_review(..., telemetry_out=usage)
   ```

   The function switches to `--format json`, parses the final verdict, and fills
   `usage`. `activities.review` must return it separately because `ReviewResult`
   has no telemetry field today; the workflow then records it in its own
   `record_step` call:

   ```python
   await workflow.execute_activity(
       act.record_step, args=["review-telemetry", json.dumps(usage),
                              json.dumps({"telemetry": usage})], **SHORT)
   ```

   or add `telemetry: dict` to `ReviewResult` and record it with the review entry.
   The receipt digest ignores `metrics`, so telemetry cannot change the
   deterministic receipt digest.

### Required PWD fix

OpenCode resolves the session directory from `PWD`, even when the process cwd is
different. A factory worker started in the release directory therefore caused
`opencode run` to edit the release checkout instead of the task worktree. Any
OpenCode step must set `PWD` to the worktree:

```python
env["PWD"] = str(wt)
```

The reviewer already sets `PWD` to its empty scratch directory. This should be
covered by a live step test before remote acceptance.

## Single OpenCode Server (verified on Railway)

The selected server is inside the `agent-factory-runtime` service in
`agent-factory-control` / `pilot` (deployment
`8165e363-6377-47e7-b776-fbfadc41864f`):

```text
process: opencode serve --service          # v2.3.0, loopback only
listen:  127.0.0.1:49374
private: agent-factory-runtime.railway.internal
public:  no domain, no TCP proxy
health:  GET /api/info                     # basic auth user "opencode"
         {"version":"2.3.0","pid":...,"urls":["http://127.0.0.1:49374"]}
web:     /global/health is the SPA, not a health probe
```

The server is co-located with `python -m agent_factory.worker` and the harness
coordinator. It is one server; do not add a second one on `the external compute host` or another
Railway service.

Factory worker command:

```bash
PWD=<task-worktree> \
HOME=/data/home XDG_DATA_HOME=/data/home/.local/share \
opencode run --format json --auto \
  -m opencode-go/deepseek-v4.1-flash "<bounded task>"
```

- `HOME=/data/home` is required. The persistent OpenCode auth store there lists
  OpenCode Go and 31 Go models. A bare SSH shell defaults to `HOME=/root` and
  returns `provider.no-route: Model unavailable`; this is an environment mistake,
  not a missing model.
- Keep `/data/home/.local/share/opencode` and `/data/home/.config/opencode` on
  the Railway volume. Never put provider keys in workflow history or task specs.
- Keep the server private and loopback-only while the worker is co-located. If a
  separate service must reach it, bind `0.0.0.0` and use the private DNS name;
  that is a new exposure decision, not the current setup.
- `FACTORY_OPENCODE_BIN` points at the pinned OpenCode v2.3.0 binary.
- The worker and server must share the same filesystem view for task worktrees.
- No `the external compute host` fallback is running. The temporary instance observed earlier was
  removed; its free-model receipt is not remote production evidence.

## Verification

Offline: `uv run pytest` passes (including the telemetry/reviewer tests).

Remote proof: synthetic `slugify` task through the Railway runtime's OpenCode
server. Coding step: 6 model calls, 6,652 input / 578 output / 189 reasoning /
39,168 cache-read tokens, 46,587 total, 15.172 s. Independent
`opencode-go/deepseek-v4.1-flash` review: `APPROVE`, 3 calls, 4,623 input / 235
output / 708 reasoning / 17,280 cache-read tokens, 22,846 total, 10.028 s.
4/4 tests pass. Combined 69,433 tokens. OpenCode reported `cost=0.0`; that is a
reported value, not proof of free routing. Receipt digest
`5a11ec0a17e3510796cfa9a72b8a32237525b23efd56100f347748c36e08bf6d`,
status `PR_OPEN`, gate `REMOTE_CODING_AND_REVIEW_PASS`.

A prior local-only proof is superseded by the Railway run. The earlier `the external compute host`
attempt used `opencode/deepseek-v4.1-flash-free` for synthetic code and recorded
a paid-model region/privacy blocker; it is not remote production evidence.
