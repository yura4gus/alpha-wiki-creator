---
name: handoff
description: "Create or validate a concise AgentOps transfer between agent roles. Use when responsibility or unfinished work moves to another role; do not create handoffs for every completed task and never paste raw logs."
---

# wiki:handoff - summarized role transfer

## Mission

Preserve continuity between agents without carrying a full transcript.

## Name Contract

`handoff` means a concise transfer of responsibility and evidence. It never
means copying the prior chat, terminal history, or chain-of-thought.

## Required Transfer

- From agent.
- To agent.
- Context summary.
- Completed work.
- Unfinished work.
- Files.
- Contracts.
- Risks.
- Decisions.
- One next action.

## Workflow

Lead with the result and decisive evidence in the user's language. Preserve
exact diagnostics and uncertainty. Run the smallest sufficient checks; reuse
results while inputs and environment match, then stop. For release decisions,
apply `references/concept.md` (Release Decisions).

1. Verify source and destination roles exist under `<wiki_dir>/agentops/agents/`.
2. Link the source session when available.
3. Summarize facts and evidence. Exclude raw logs, chain-of-thought, secrets,
   terminal dumps, and repeated source documents.
4. Create the handoff:

```bash
python3 .alpha-wiki/run.py -m tools.handoff create --wiki-dir <wiki_dir> ...
```

5. Validate all handoffs with:

```bash
python3 .alpha-wiki/run.py -m tools.handoff validate --wiki-dir <wiki_dir>
```

## Codex Native Delegation

The controller creates the final handoff after synthesizing terminal agent
results. A subagent may draft its own concise result envelope, but it does not
choose the receiving owner or mutate shared handoff state.

## Done Criteria

- The receiving role can act without reading the prior raw session.
- Facts, unknowns, risks, and owner decisions are distinguishable.
- The next action is singular and executable.

## References

- `tools/handoff.py`
- `references/agentops-control-layer.md`
- `references/codex-subagent-orchestration.md`
