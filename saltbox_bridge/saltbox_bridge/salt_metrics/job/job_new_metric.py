from __future__ import annotations

import re
from time import time

from prometheus_client import Counter

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.job.base_job_metric import BaseJobMetric


class JobNewMetric(BaseJobMetric):

    _TAG_PATTERN = re.compile(r'^salt/job/(?P<jid>\d{20})(?:-t(?P<tid>[a-f0-9]{24}))?/new$')

    def can_handle(self, tag: str) -> bool:
        return bool(self.tag_pattern.match(tag))

    @property
    def labels(self) -> list[str]:
        return ['master', 'fun']

    def _create(self) -> Counter:
        return Counter(
            name=self.name,
            documentation=self.desc,
            labelnames=self.labels,
            registry=self.registry
        )

    @property
    def tag_pattern(self) -> re.Pattern:
        return self._TAG_PATTERN

    async def _aggregate(self, jid: str, tid: str | None, data: MessageDataType) -> None:
        redis_key = f'job:{jid}{"-t" + tid if tid else ""}:new_time'
        await self.redis_client.set(name=redis_key, value=time())
        self.metric.labels(
            master=self.master,
            fun=data['fun'],
        ).inc()  # type: ignore[attr-defined]
