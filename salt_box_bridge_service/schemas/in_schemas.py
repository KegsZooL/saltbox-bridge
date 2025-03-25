from __future__ import annotations

from salt_box_bridge_service.schemas.base_schemas import BaseInMessage


class NewJobIneMessage(BaseInMessage):
    hash_name: str


class GatherMinionsInMessage(BaseInMessage):
    tgt: str
    tgt_type: str


class PingInMessage(BaseInMessage): ...
