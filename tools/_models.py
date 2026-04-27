from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LintSeverity(str, Enum):
    ERROR = "error"      # blocks
    WARNING = "warning"  # warning
    OK = "ok"            # ok


@dataclass
class Page:
    slug: str
    title: str
    path: str  # relative to wiki dir, e.g. "modules/auth.md"
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    forward_links: list[str] = field(default_factory=list)


@dataclass
class Edge:
    source: str   # page slug
    target: str   # page slug
    relation: str # e.g. "depends_on", "provides", "supersedes"

    def to_jsonl(self) -> str:
        import json
        return json.dumps({"source": self.source, "target": self.target, "relation": self.relation})


@dataclass
class LintFinding:
    check: str
    severity: LintSeverity
    file: str
    line: int
    message: str
    fix_available: bool = False
    suggested_fix: str | None = None
