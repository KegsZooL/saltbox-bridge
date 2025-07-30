from __future__ import annotations

import logging
from time import time

import redis.asyncio as redis
from prometheus_client import Counter
from prometheus_client.metrics import MetricWrapperBase

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import BaseMetric

logger = logging.getLogger(__name__)


class JobNewMetric(BaseMetric):

    def _create(self) -> MetricWrapperBase:
        return Counter(
            name=self.name, documentation=self.desc, labelnames=self.labels, registry=self.registry)

    async def aggregate(self, master: str, jid: str, data: MessageDataType, redis_client: redis.Redis) -> None:
        if self.metric:
            timestamp = time()
            await redis_client.set(name=f'job:{jid}:new_time', value=timestamp)
            self.metric.labels(
                master=master,
                fun=data['fun'],
                minions=data['minions']
            ).inc()
            logger.debug("Metric '%s' has been increased (Master: '%s')", self.name, master)
