from __future__ import annotations

import abc
from typing import TYPE_CHECKING

import redis.asyncio as redis
from prometheus_client import CollectorRegistry
from prometheus_client.metrics import MetricWrapperBase

if TYPE_CHECKING:
    from saltbox_bridge.salt_handlers.base_handler import MessageDataType


class BaseMetric(abc.ABC):
    """
    A base class for handling prometheus metrics

    Attributes:
        registry: Registry of acceptable metrics
        name: Metric name
        desc: Description of the metric
        labels: Labels for the metric
        metric: The metric instance (e.g, Counter, Gauge, etc...)
    """
    def __init__(
            self, registry: CollectorRegistry,
            name: str, desc: str,
            labels: list[str] | None,
    ) -> None:
        self.name = name
        self.desc = desc
        self.labels = labels
        self.registry = registry
        self.metric = self._create()

    @abc.abstractmethod
    def _create(self) -> MetricWrapperBase: ...

    @abc.abstractmethod
    async def aggregate(
        self,
        master: str,
        jid: str,
        data: MessageDataType,
        redis_client: redis.Redis,
    ) -> None: ...
