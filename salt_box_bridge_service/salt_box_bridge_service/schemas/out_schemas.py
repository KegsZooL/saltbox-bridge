from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, PositiveInt

from salt_box_bridge_service.schemas.base_schemas import BaseOutMessage


class Minion(BaseModel):
    minion_id: str
    master: str


class PresenceOutMessage(BaseOutMessage):
    minions: list[str]
    stamp: float


class GrainsOutMessage(BaseOutMessage):
    grains: dict[str, Any]


class GatherMinionsOutMessage(BaseOutMessage):
    count: Annotated[int, PositiveInt]
    minions: list[Minion]
