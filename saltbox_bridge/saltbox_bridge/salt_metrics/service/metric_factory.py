from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from exceptions import InvalidMetricClassError  # type: ignore[import-not-found]

from prometheus_client import CollectorRegistry
from redis import asyncio as aioredis

from saltbox_bridge.salt_metrics.base_metric import BaseMetric
from saltbox_bridge.salt_metrics.metric_specification import METRIC_SPECIFICATIONS

logger = logging.getLogger(__name__)


class MetricFactory:
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

    def _create_metric(self, specification: dict[str, Any]) -> BaseMetric:
        if specification is not None:
            metric_class = specification['class']
            if issubclass(metric_class, BaseMetric):
                key = specification['key']
                self._instances[key] = metric_class(
                    registry=self._registry,
                    name=key,
                    desc=specification['desc'],
                    labels=specification['labels'],
                    redis_client=self._redis_client,
                    salt_opts=self._salt_opts
                )
            else:
                msg = f'Metric class {metric_class} does not extend BaseMetric class'
                raise InvalidMetricClassError(msg)

        return self._instances[specification['key']]

    def create_all(self) -> list[BaseMetric]:
        return [self._create_metric(specification=s) for s in METRIC_SPECIFICATIONS]
