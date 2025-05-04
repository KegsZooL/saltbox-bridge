from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PositiveInt

from saltbox_bridge.schemas.base_schemas import BaseOutMessage
from saltbox_bridge.utils.types import SaltTgtType


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


class JobReturn(BaseModel):
    ret: Any
    retcode: int
    jid: str

    model_config = ConfigDict(extra='allow')


class JobSyncOutMessage(BaseOutMessage):
    jid: str
    tgt: str
    tgt_type: SaltTgtType
    fun: str
    arg: list
    kwarg: dict
    returns: dict[str, JobReturn]
