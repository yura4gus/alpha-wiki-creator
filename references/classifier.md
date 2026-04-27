# Artifact classifier

`tools/classify.py` decides which entity-type slot a raw file maps to.

## Strategy

1. **Extension + filename heuristics** (deterministic, no LLM)
2. **Frontmatter sniff** (if `.md` with YAML frontmatter)
3. **MIME inspection** (for ambiguous binaries)
4. **LLM fallback** (only if deterministic checks return None) — calls Claude with the file head

## Recognized classes (out of the box)

| Class | Detect by | Default slot (software-project) |
|---|---|---|
| OpenAPI spec | `*.yaml/*.json` w/ `openapi:` key | `contracts/rest/` |
| GraphQL schema | `*.graphql`, `*.gql` | `contracts/graphql/` |
| protobuf | `*.proto` | `contracts/grpc/` |
| AsyncAPI | `*.yaml/*.json` w/ `asyncapi:` key | `contracts/events/` |
| ADR | `*.md` w/ frontmatter `kind: adr` or filename `adr-*` | `decisions/` |
| C4/PlantUML | `*.puml`, `*.mermaid`, `*.dot` | `specs/` (with `kind: diagram`) |
| Source code | `*.py`, `*.ts`, `*.go`, ... | (skipped — not ingested) |
| Migration | `*.sql` w/ `CREATE TABLE` or filename `*_migration.sql` | (no default slot — triggers schema-evolve) |
| Terraform | `*.tf` | (no default slot — triggers schema-evolve) |
| K8s manifest | `*.yaml` w/ `apiVersion:` and `kind:` | (no default slot — triggers schema-evolve) |
| PRD/RFC | `*.md` w/ frontmatter `kind: prd` or filename `PRD*` / `RFC*` | `specs/` |
| Threat model | `*.md` w/ frontmatter `kind: threat-model` | `specs/` (with `kind: security`) |
| Runbook | `*.md` w/ frontmatter `kind: runbook` | `specs/` (with `kind: ops`) |
| Postmortem | `*.md` w/ filename `postmortem-*` | `decisions/` (with `kind: postmortem`) |
| Meeting transcript | `*.md`/`*.txt` w/ frontmatter `kind: transcript` or under `raw/transcripts/` | (extract → ingest as multiple pages) |
| Slack export | `.json` from Slack export | (extract → multiple pages) |
| Test plan | `*.md` w/ frontmatter `kind: test-plan` | `specs/` |
| Postman collection | `*.postman_collection.json` | `contracts/rest/` (with `kind: collection`) |
| SQL DDL | `*.sql` w/ `CREATE TABLE` | (triggers schema-evolve to `data/schema/`) |
| JSON Schema | `*.schema.json` | `contracts/data-models/` |
| Avro | `*.avsc` | `contracts/data-models/` |

Other file types fall through to schema-evolve flow.
