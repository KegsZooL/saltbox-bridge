from __future__ import annotations

from salt_box_bridge_service.schemas.base_schemas import BaseInMessage
from salt_box_bridge_service.utils.types import SaltTgtType


class NewJobIneMessage(BaseInMessage):
    hash_name: str


class GatherMinionsInMessage(BaseInMessage):
    tgt: str
    tgt_type: SaltTgtType


class PingInMessage(BaseInMessage): ...
