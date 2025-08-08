from __future__ import annotations

import abc
import re

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import BaseMetric


class BaseJobMetric(BaseMetric, abc.ABC):
    """
    A base metric class for handling salt job event
    """
    @property
    @abc.abstractmethod
    def tag_pattern(self) -> re.Pattern: ...

    @abc.abstractmethod
    async def _aggregate(self, jid: str, tid: str | None, data: MessageDataType) -> None: ...

    async def aggregate(self, tag: str, data: MessageDataType) -> None:
        match = self.tag_pattern.match(tag)
        if match:
            jid = match.group('jid')
            tid = match.group('tid')
            await self._aggregate(jid=jid, tid=tid, data=data)
