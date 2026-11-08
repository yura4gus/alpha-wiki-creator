# Alpha-Wiki architecture pilot

The optional OpenFlowKit harness reads a clean Git checkout at an exact SHA.
It renders a static repository map, a draft discovered model, the curated
reference diagrams, and an offline Canvas site. The [product roadmap](../roadmap-execution.md)
owns priorities and pilot acceptance. [SPEC.md](SPEC.md) retains the supplied
proposal and its acceptance criteria.

## Run locally

Use Python 3.12 or later, Node.js 20.11 or later, Git, and a checkout approved
for local inspection. The first run fetches `openflowkit@0.3.0` from npm.
Run from the Alpha-Wiki source checkout:

```bash
uv run --no-project --python 3.12 python scripts/openflowkit_pilot.py /path/to/clean-checkout \
  --sha <full-sha> --out /path/outside-both-checkouts/new-output
```

Open `repo-map.html` or `canvas-site/index.html` locally. Open a generated
`*.openflow.json` document in Canvas to inspect or edit it. Preserve the
original DSL for its comments, source references, and reusable model.
The static map scans a Git archive. The archive excludes working files,
ignored files and Git metadata. Source paths are relative to the snapshot.
GitHub evidence hyperlinks are unavailable in this archive mode.

`discovery.ofk` is a machine-observed draft. `architecture/architecture.ofk`
and the companion workflow diagrams describe the proposed cross-system setup.
`architecture/agentops-state-contract.ofk` shows the declared and observed
local Markdown boundary from ADR-007 at the stated SHA. The scoped diagram
records static evidence. It conveys no runtime health or deployment status.

Pass an earlier successful `report.json` from the same repository with
`--baseline` to compare a clean revision against its pinned discovery.
The baseline hash detects edits to its DSL. Exit 0 means the static comparison
passed, 1 means drift, and 2 means the harness could not prove a result.
The CLI smoke runs the same discovery and drift commands in an isolated
fixture and is part of plugin CI:

```bash
uv run --no-project --python 3.12 bash scripts/openflowkit_smoke.sh /path/to/new-output
```

## Alpha-Wiki Harness² profile

Run the optional evidence replay with the pinned
[Google Harness² engine](https://github.com/google-research/harness2/tree/6868817518876de8fd170c6a8354daca273b6191).
It uses a deterministic executor and editor, with one challenge and two
holdouts. The engine and its dependencies stay outside Alpha-Wiki's
installed plugin runtime.

```bash
uv run --no-project --python 3.12 \
  --with 'harness2 @ git+https://github.com/google-research/harness2.git@6868817518876de8fd170c6a8354daca273b6191' \
  python scripts/harness2_alpha_wiki.py --out /path/to/new-evaluation
```

The replay checks source provenance without model calls. Its candidate and
run receipts stay in the chosen output directory. A live model experiment
and reviewed adoption have separate acceptance.

For local MCP, scope `npx --yes openflowkit@0.3.0 mcp` to the writer's test
session. Expose only the tools needed for that session. Reviewers receive a
bounded packet with no diagram-write permissions. Keep xPlan task links and
revision readback in the controller's separate evidence receipt. The
OpenFlowKit commands have no task transition path.
