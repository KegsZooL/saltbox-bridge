from __future__ import annotations

import logging
import re
from time import time

from prometheus_client import Counter

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import JobBaseMetric

logger = logging.getLogger(__name__)


class JobNewMetric(JobBaseMetric):

    _TAG_PATTERN = re.compile(r'^salt/job/(?P<jid>\d{20})/new$')

    def can_handle(self, tag: str) -> bool:
        return bool(self.tag_pattern.match(tag))

    @property
    def labels(self) -> list[str]:
        return ['master', 'fun', 'minions']

    def _create(self) -> Counter:
        return Counter(
            name=self.name, documentation=self.desc, labelnames=self.labels, registry=self.registry)

    @property
    def tag_pattern(self) -> re.Pattern:
        return self._TAG_PATTERN

    async def _aggregate(self, jid: str, data: MessageDataType) -> None:
        timestamp = time()
        await self.redis_client.set(name=f'job:{jid}:new_time', value=timestamp)
        self.metric.labels(
            master=self.master,
            fun=data['fun'],
            minions=data['minions']
        ).inc()  # type: ignore[attr-defined]
        logger.debug("Metric '%s' has been increased (Master: '%s')", self.name, self.master)
