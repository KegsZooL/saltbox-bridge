# FIXME (a.karmanov) US317: DELETE due to lib

from __future__ import annotations

from saltbox_bridge_messages import BridgeMessageBase


class PresenceMessage(BridgeMessageBase):
    minions: list[str]
    stamp: float
