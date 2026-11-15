"""Opt-in fault injection for recovery tests. Inert unless FACTORY_FAULTS is set.

Format: `point@index=action[,..]` (index optional), action is `crash` or `error`.
Each fault fires once; a marker in the durable state dir remembers it.
"""

from __future__ import annotations

import os
from pathlib import Path


def hit(state_dir: Path, point: str, index: int | None = None) -> str | None:
    raw = os.environ.get("FACTORY_FAULTS")
    if not raw:
        return None
    for item in raw.split(","):
        target, _, action = item.partition("=")
        name, _, idx = target.partition("@")
        if name != point or (idx and index is not None and int(idx) != index):
            continue
        marker = Path(state_dir) / "faults" / f"{point}-{index}"
        if marker.exists():
            return None
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(action)
        return action
    return None
