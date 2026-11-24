"""Worker-local configuration.

Two roots with different durability:
- work_root: ephemeral per worker host (clones, worktrees, logs). May be lost.
- state_dir: durable shared state (receipts, local PR registry, fault markers).
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    work_root: Path
    state_dir: Path

    @classmethod
    def from_env(cls) -> "Config":
        base = Path(os.environ.get("FACTORY_HOME", Path.home() / ".agent-factory"))
        return cls(
            work_root=Path(os.environ.get("FACTORY_WORK_ROOT", base / "work")),
            state_dir=Path(os.environ.get("FACTORY_STATE_DIR", base / "state")),
        )
