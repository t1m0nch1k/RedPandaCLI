from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).parent / "catalog.json"


def get_catalog_entries() -> list[dict[str, Any]]:
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return data.get("providers", [])
    except (json.JSONDecodeError, OSError):
        return []


def find_in_catalog(name: str) -> dict[str, Any] | None:
    for entry in get_catalog_entries():
        if entry["name"] == name:
            return entry
    return None


def get_catalog_names() -> list[str]:
    return [e["name"] for e in get_catalog_entries()]
