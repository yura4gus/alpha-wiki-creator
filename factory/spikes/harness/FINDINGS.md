# Temporal Agent Harness spike (2026-11-14)

Scope: install `temporal-agent-harness==0.11.0` (experimental, MIT) in a throwaway
venv and read its API against the Factory's needs. **No live agent run**: that needs
a model credential and an AI SDK extra, which were not provided. Findings below come
from the installed package source and metadata, not from execution.

## What it provides (source-confirmed)
| Capability | Where | Notes |
|---|---|---|
| Durable sessions | `harness/state/session.py`, `agent_workflow.py` | agent = workflow |
| Tool approval | `agent_interface.py`: `ToolApprovalPolicy`, `PendingApproval`, Update `tool_approval` | policy-based, with an auto-approval mode |
| Subagents | `subagent_toolset.py`, `RunSubagentTurnInput`, `SubagentInfo` | typed, run as turns |
| Steering / streaming | `steering.py`, `stream_merge/` | mid-turn messages |
| Agent loop | `ai_sdks/{openai_agents,strands_agents,google_genai_plugin,pydantic_ai_harness}` | the **SDK's** loop, not an external CLI |

## What it does not provide
- No driver for external CLI agents (OpenCode, Codex): the only subprocess use is the
  code-mode `monty` sandbox. A CLI would have to be wrapped as a custom tool, which
  gives up the harness's per-tool approval and streaming for that tool.
- No git worktree handling and no checkpoint/resume of a filesystem.
- Requires a model SDK and credentials for any real run.

## Comparison with the CLI adapter (`activities.agent_step`)
| Criterion | CLI adapter (adopted) | Agent Harness |
|---|---|---|
| Keeps OpenCode/Codex native loops | yes | no, replaces them with an SDK loop |
| Worktree isolation + checkpoint recovery | yes, tested (CRASH) | not offered |
| Durable approval | Update `decide`, tested (APPROVAL) | yes, per tool call |
| Subagents | not needed in V1 | yes |
| Maturity | tested here, our code | experimental, all releases pre-release |

## Decision
Do not adopt the harness as the V1 executor. Keep Temporal Core plus the thin CLI
adapter. Revisit if the Factory runs its own LLM loop instead of vendor CLIs: its
per-tool approvals, subagent turns and session manager would then be reusable.
Open items: measure it live with credentials; confirm API stability across releases.
