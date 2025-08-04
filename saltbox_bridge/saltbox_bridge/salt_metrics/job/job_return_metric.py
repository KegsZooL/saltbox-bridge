from __future__ import annotations

import logging
import re
from time import time

from prometheus_client import Gauge

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import JobBaseMetric

logger = logging.getLogger(__name__)


class JobReturnMetric(JobBaseMetric):

    _TAG_PATTERN = re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)')

    def can_handle(self, tag: str) -> bool:
        return bool(self.tag_pattern.match(tag))

    @property
    def labels(self) -> list[str]:
        return ['master', 'minion_id']

    def _create(self) -> Gauge:
        return Gauge(
            name=self.name,
            documentation=self.desc,
            labelnames=self.labels,
            registry=self.registry
        )

    @property
    def tag_pattern(self) -> re.Pattern:
        return self._TAG_PATTERN

    async def _aggregate(self, jid: str, data: MessageDataType) -> None:
        job_creation_time = await self.redis_client.get(name=f'job:{jid}:new_time')
        if job_creation_time is not None:
            job_creation_time = float(job_creation_time)
            duration = await self._set_job_duration(job_creation_time=job_creation_time, data=data)
            logger.debug('Job %s processing time: %f seconds', jid, duration)
        else:
            logger.info("Failed to extract job creation time from redis | jid: %s", jid)

    async def _set_job_duration(self, job_creation_time: float, data: MessageDataType) -> float:
        job_creation_time = float(job_creation_time)
        job_return_time = time()
        time_diff = job_return_time - job_creation_time

        self.metric.labels(
                master=self.master,
                minion_id=data['id'],
            ).set(value=time_diff)  # type: ignore[attr-defined]
        return time_diff
