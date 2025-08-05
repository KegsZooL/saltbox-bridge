from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry
from redis import asyncio as aioredis

from saltbox_bridge.salt_metrics.base_metric import BaseMetric
from saltbox_bridge.salt_metrics.metric_specification import METRIC_SPECS

logger = logging.getLogger(__name__)


class MetricsRegistry:
    def __init__(
            self,
            registry: CollectorRegistry,
            redis_client: aioredis.Redis,
            salt_opts: dict,
    ) -> None:
        self._registry = registry
        self._redis_client = redis_client
        self._salt_opts = salt_opts
        self._instances: dict[str, BaseMetric] = {}

    def _get(self, spec: dict) -> BaseMetric:
        if spec is not None:
            metric_clazz = spec['clazz']
            if issubclass(metric_clazz, BaseMetric):
                key = spec['key']
                self._instances[key] = metric_clazz(
                    registry=self._registry,
                    name=key,
                    desc=spec['desc'],
                    labels=spec['labels'],
                    redis_client=self._redis_client,
                    salt_opts=self._salt_opts
                )
            else:
                logger.error('Metric class &s does not extend BaseMetric class', metric_clazz)
        return self._instances[spec['key']]

    def create_all(self) -> list[BaseMetric]:
        return [self._get(spec) for spec in METRIC_SPECS]
