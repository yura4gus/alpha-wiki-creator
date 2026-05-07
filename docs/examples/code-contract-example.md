# Code Contract Example

Purpose: show how Alpha-Wiki records a code invariant that agents must respect. This does not replace tests or source code.

```yaml
title: Private Key Custody Boundary
slug: private-key-custody-boundary
kind: code-contract
status: stable
belongs_to: "[[wallet-module]]"
source_file: src/wallet/custody.ts
tests:
  - tests/wallet/custody.test.ts
date_updated: 2026-05-07
```

## Invariant

Backend services must never receive raw user private keys.

## Boundary

- Owner/module: [[wallet-module]]
- Allowed location: frontend custody code only.
- Forbidden change: adding API fields, logs, jobs, or telemetry that transmit private keys to backend services.
- Expected behavior: backend receives signed requests or encrypted payloads, never raw keys.

## Why It Matters

Breaking this contract changes the security model and requires explicit architecture review, tests, and migration notes.

## Related Files

- `src/wallet/custody.ts`
- `tests/wallet/custody.test.ts`

