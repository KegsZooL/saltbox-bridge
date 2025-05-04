from __future__ import annotations

from saltbox_bridge.schemas.base_schemas import BaseInMessage
from saltbox_bridge.utils.types import SaltTgtType


class NewJobIneMessage(BaseInMessage):
    hash_name: str


class NewJobSyncIneMessage(BaseInMessage):
    tgt: str
    tgt_type: SaltTgtType
    fun: str
    arg: list
    kwarg: dict
    jid: str | None = None


class GatherMinionsInMessage(BaseInMessage):
    tgt: str
    tgt_type: SaltTgtType


class UpdatePillarCacheInMessage(BaseInMessage):
    tgt: str
    tgt_type: SaltTgtType


class PingInMessage(BaseInMessage): ...
