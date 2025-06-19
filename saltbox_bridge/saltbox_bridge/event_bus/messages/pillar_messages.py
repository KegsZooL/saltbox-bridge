from __future__ import annotations

from saltbox_bridge_messages import BridgeMessageBase, SaltTgtType


class UpdatePillarCacheInMessage(BridgeMessageBase):
    tgt: str
    tgt_type: SaltTgtType
