from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict
from saltbox_bridge_messages import BridgeMessageBase, SaltTgtType


class NewJobIneMessage(BridgeMessageBase):
    hash_name: str


class NewJobSyncIneMessage(BridgeMessageBase):
    tgt: str
    tgt_type: SaltTgtType
    fun: str
    arg: list
    kwarg: dict
    jid: str | None = None


class JobReturn(BaseModel):
    ret: Any
    retcode: int
    jid: str

    model_config = ConfigDict(extra='allow')


class JobSyncOutMessage(BridgeMessageBase):
    jid: str
    tgt: str
    tgt_type: SaltTgtType
    fun: str
    arg: list
    kwarg: dict
    returns: dict[str, JobReturn]
