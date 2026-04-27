"""Loads ~/.env then ./.env (local overrides home)."""
from __future__ import annotations
import os
from pathlib import Path


def _parse_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def load_env() -> None:
    home_env = _parse_dotenv(Path.home() / ".env")
    local_env = _parse_dotenv(Path.cwd() / ".env")
    for k, v in {**home_env, **local_env}.items():
        os.environ[k] = v  # local overrides home
