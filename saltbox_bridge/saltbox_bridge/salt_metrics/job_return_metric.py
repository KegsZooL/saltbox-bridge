from __future__ import annotations

import logging
from time import time

import redis.asyncio as redis
from prometheus_client import Gauge
from prometheus_client.metrics import MetricWrapperBase

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import BaseMetric

logger = logging.getLogger(__name__)


class JobReturnMetric(BaseMetric):

    def _create(self) -> MetricWrapperBase:
        return Gauge(
            name=self.name,
            documentation=self.desc,
            labelnames=self.labels,
            registry=self.registry
        )

    async def aggregate(self, master: str, jid: str, data: MessageDataType, redis_client: redis.Redis) -> None:
        if self.metric:
            job_new_time = await redis_client.get(name=f'job:{jid}:new_time')
            if job_new_time:
                job_new_time = float(job_new_time)
                job_return_time = time()
                time_diff = job_return_time - job_new_time

                self.metric.labels(
                    master=master,
                    minion_id=data['id'],
                ).set(time_diff)
                logger.debug('Job %s processing time: %f seconds', jid, time_diff)
            else:
                logger.info("Failed to extract job creation time from redis | jid: %s", jid)
