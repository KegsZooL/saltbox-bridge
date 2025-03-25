from __future__ import annotations

from typing import Any

from salt_box_bridge_service.schemas.base_schemas import BaseOutMessage


class PresenceOutMessage(BaseOutMessage):
    minions: list[str]
    stamp: float


class GrainsOutMessage(BaseOutMessage):
    grains: dict[str, Any]
