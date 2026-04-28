"""Artifact classifier — extension first, LLM fallback (stub)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class Artifact:
    kind: str
    suggested_slot: str | None
    confidence: float  # 0.0-1.0
    detected_by: str   # "extension" | "frontmatter" | "llm" | ...


def classify(path: Path) -> Artifact:
    """Classify an artifact by extension and content inspection.

    Returns an Artifact with kind, suggested_slot, confidence, and detection method.
    """
    name = path.name.lower()
    suffix = path.suffix.lower()
    head = path.read_text(errors="ignore")[:2000] if path.is_file() else ""

    if suffix in (".yaml", ".yml") and "openapi:" in head:
        return Artifact("openapi", "contracts/rest", 0.95, "extension+content")
    if suffix in (".yaml", ".yml") and "asyncapi:" in head:
        return Artifact("asyncapi", "contracts/events", 0.95, "extension+content")
    if suffix in (".graphql", ".gql"):
        return Artifact("graphql-schema", "contracts/graphql", 0.95, "extension")
    if suffix == ".proto":
        return Artifact("protobuf", "contracts/grpc", 0.95, "extension")
    if suffix == ".sql" and "create table" in head.lower():
        return Artifact("sql-ddl", None, 0.90, "extension+content")
    if suffix == ".tf":
        return Artifact("terraform", None, 0.85, "extension")
    if suffix == ".md":
        if "kind: adr" in head or name.startswith("adr-"):
            return Artifact("adr", "decisions", 0.90, "frontmatter+filename")
        if "kind: prd" in head or name.startswith("prd"):
            return Artifact("prd", "specs", 0.90, "frontmatter+filename")
        if "kind: rfc" in head or name.startswith("rfc"):
            return Artifact("rfc", "specs", 0.90, "frontmatter+filename")
        if "kind: runbook" in head:
            return Artifact("runbook", "specs", 0.85, "frontmatter")
        if "kind: postmortem" in head or "postmortem" in name:
            return Artifact("postmortem", "decisions", 0.85, "frontmatter+filename")
        if "kind: transcript" in head:
            return Artifact("transcript", None, 0.80, "frontmatter")
        return Artifact("markdown", None, 0.50, "extension")
    if suffix == ".puml" or suffix == ".mermaid":
        return Artifact("diagram", "specs", 0.85, "extension")
    if suffix == ".postman_collection.json" or name.endswith(".postman_collection.json"):
        return Artifact("postman-collection", "contracts/rest", 0.90, "extension")

    return Artifact("unknown", None, 0.0, "fallback")


def classify_llm_fallback(path: Path) -> Artifact | None:
    """LLM-based classification stub. Returns None if no API key configured.

    A real implementation would call Claude with the file head + ask for kind.
    For initial release, we ship the stub and rely on extension classification.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    # TODO(later): implement actual LLM call. Until then, return None.
    return None
