from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry
from redis import asyncio as aioredis

from saltbox_bridge.salt_metrics.base_metric import BaseMetric
from saltbox_bridge.salt_metrics.metric_settings import METRIC_SPECS

logger = logging.getLogger(__name__)


class MetricsRegistry:
    def __init__(
            self,
            registry: CollectorRegistry,
            redis_client: aioredis.Redis,
            salt_opts: dict,
            specs: list[dict] = METRIC_SPECS
    ) -> None:
        self._registry = registry
        self._redis_client = redis_client
        self._salt_opts = salt_opts
        self._specs = specs
        self._instances: dict[str, BaseMetric] = {}

    def __get(self, key: str) -> BaseMetric:
        if key not in self._instances:
            spec = next((spec for spec in self._specs if spec['key'] == key), None)
            if spec is not None:
                self._instances[key] = spec['clazz'](
                    registry=self._registry,
                    name=key,
                    desc=spec['desc'],
                    labels=spec['labels'],
                    redis_client=self._redis_client,
                    salt_opts=self._salt_opts
                )
            else:
                logger.error('No metric spec found for key: %s', key)
        return self._instances[key]

    def create_all(self) -> list[BaseMetric]:
        return [self.__get(spec['key']) for spec in self._specs]
