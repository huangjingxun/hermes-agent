"""Identity and room registry for memory tag isolation.

Reads ~/.hermes/config/memory/identity-registry.json and
room-registry.json to resolve platform+chat_id → identity mapping.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def get_config_memory_dir() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "config" / "memory"


def _load_json(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_identity(platform: str, chat_id: str) -> tuple[str, str] | None:
    """Resolve platform+chat_id to (identity_name, role).
    
    identity_name falls back to the matched alias's chat_id when the
    JSON entry has no explicit name field (统一 identity = chat_id).
    Returns None if not found and registry empty.
    """
    if not platform or not chat_id:
        return None
    path = get_config_memory_dir() / "identity-registry.json"
    data = _load_json(path)
    for identity in data.get("identities", []):
        for alias in identity.get("aliases", []):
            if alias.get("platform") == platform and alias.get("chat_id") == chat_id:
                name = identity.get("name") or alias.get("chat_id", "")
                return name, identity.get("role", "user")
    return None


def auto_register_identity(platform: str, chat_id: str) -> tuple[str, str]:
    """Auto-register unknown user as role:user with one alias.
    
    Identity name = chat_id, label = chat_id (统一使用 chat_id).
    Returns (identity_name, role).
    """
    path = get_config_memory_dir() / "identity-registry.json"
    data = _load_json(path)
    identities = data.get("identities", [])

    # Check if already exists
    for identity in identities:
        for alias in identity.get("aliases", []):
            if alias.get("platform") == platform and alias.get("chat_id") == chat_id:
                name = identity.get("name") or alias.get("chat_id", "")
                return name, identity.get("role", "user")

    # Use chat_id as both identity name and label
    resolved_name = chat_id or "unknown"

    new_identity = {
        "role": "user",
        "aliases": [{"platform": platform, "chat_id": chat_id, "label": chat_id}]
    }
    identities.append(new_identity)
    data["identities"] = identities
    _save_json(path, data)
    return resolved_name, "user"


def get_identity_aliases(identity_name: str) -> list[dict[str, str]]:
    """Get all aliases for a given identity name.
    
    Falls back to matching against first alias's chat_id when the JSON
    entry has no explicit name field (统一 identity = chat_id).
    
    Used for cross-platform recall (all_platforms scope).
    """
    path = get_config_memory_dir() / "identity-registry.json"
    data = _load_json(path)
    for identity in data.get("identities", []):
        entry_name = identity.get("name") or (identity.get("aliases", [{}])[0].get("chat_id", ""))
        if entry_name == identity_name:
            return list(identity.get("aliases", []))
    return []


def resolve_room_room_id(platform: str, room_id: str) -> dict[str, Any] | None:
    """Resolve room by platform+room_id."""
    if not platform or not room_id:
        return None
    path = get_config_memory_dir() / "room-registry.json"
    data = _load_json(path)
    for room in data.get("rooms", []):
        if room.get("platform") == platform and room.get("room_id") == room_id:
            return room
    return None


def auto_register_room(platform: str, room_id: str, room_name: str = "") -> dict[str, Any]:
    """Auto-register unknown room with basic info."""
    path = get_config_memory_dir() / "room-registry.json"
    data = _load_json(path)
    rooms = data.get("rooms", [])
    
    for room in rooms:
        if room.get("platform") == platform and room.get("room_id") == room_id:
            return room
    
    from datetime import datetime, timezone
    new_room = {
        "room_id": room_id,
        "platform": platform,
        "room_name": room_name or room_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "known_members": [],
        "description": ""
    }
    rooms.append(new_room)
    data["rooms"] = rooms
    _save_json(path, data)
    return new_room
