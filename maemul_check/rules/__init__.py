"""룰 JSON 로더."""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).parent


@cache
def load(name: str) -> dict[str, Any]:
    """rules/<name>.json 을 읽는다. (예: load("purpose_map"))"""
    with (RULES_DIR / f"{name}.json").open(encoding="utf-8") as f:
        return json.load(f)
