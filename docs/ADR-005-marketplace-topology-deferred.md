# ADR-005 — Marketplace topology deferred to Phase 5

**Status**: Accepted
**Date**: 2026-04-29

## Context

Alpha-Wiki is already published as `yura4gus/alpha-wiki-creator` and installable via `claude plugins marketplace add yura4gus/alpha-wiki-creator`. Existing users are on this path.

AgentOps is a new plugin. It must ship somewhere. Options considered:

- **A**: Repurpose `yura4gus/alpha-wiki-creator` as a marketplace root containing both plugins.
- **B**: Keep `yura4gus/alpha-wiki-creator` as-is. Create a new repo for AgentOps. No umbrella marketplace.
- **C**: Create a third repo as an umbrella marketplace listing both plugins.

## Decision

**Option B** for Phase 1, with **Option C deferred to Phase 5**.

Phase 1 stance:

1. `yura4gus/alpha-wiki-creator` continues unchanged as a standalone published plugin. Phase 1a hardens it in place. No rename, no restructure, no relocation.
2. AgentOps starts as a separate plugin in a separate repository (working name: `agentops`, owner TBD).
3. No umbrella marketplace is created. Users install each plugin independently.

Phase 5 stance:

After both plugins reach stable releases and the integration matrix is validated, evaluate creating an umbrella marketplace listing both. Decision criteria for Phase 5: existing user count, demand signals, marketplace ecosystem norms at that time. If created, the umbrella points at the existing repos; it does not absorb them.

## Reasoning

1. **Do not disrupt published plugin users.** Renaming or relocating `alpha-wiki-creator` would break existing installations and goodwill.
2. **Architecture not yet stable.** A marketplace topology should be decided when the architecture is proven, not before the second plugin even exists.
3. **Composability is the goal, not packaging.** Two independently-installable plugins prove the boundary. An umbrella marketplace can be added later without changing the underlying repos.
4. **Lowest commitment is best now.** Two repos, two plugins. Add umbrella only when there is a concrete reason.

## Alternatives rejected

- **Option A — repurpose existing repo as marketplace root.** Rejected: forces a rename or restructure of a published plugin, breaks existing users, premature.
- **Option C immediately.** Rejected: premature; commits to a topology before the second plugin has shipped a single release.
- **Sub-plugins under one repo without marketplace.** Rejected: Claude Code plugin tooling does not natively support sub-plugin packaging in a way that gives clean independent versioning.

## Risks

- **Discoverability** of AgentOps may be lower without an umbrella. Mitigation: README of `alpha-wiki-creator` links to AgentOps; AgentOps README links back. Cross-references in documentation.
- **Repository sprawl** if more layers are added later. Mitigation: revisit in Phase 5 with concrete usage data.

## Validation

- Phase 1a hardens `alpha-wiki-creator` in place; no path or namespace changes externally visible.
- Phase 1b creates the AgentOps repo as a clean second plugin.
- Both install via standard Claude Code plugin commands without an umbrella marketplace.
- Phase 5 revisits the topology decision with criteria (user count, demand) documented at that time.
