from __future__ import annotations

import abc

import redis.asyncio as redis
from prometheus_client import CollectorRegistry
from prometheus_client.metrics import MetricWrapperBase

from saltbox_bridge.salt_handlers.base_handler import MessageDataType


class BaseMetric(abc.ABC):
    """
    A base class for handling prometheus metrics

    Attributes:
        registry: Registry of acceptable metrics
        name: Metric name
        desc: Description of the metric
        redis_client: Redis client
        labels: Labels displayed in Grafana UI
        salt_opts: Master config
    """
    def __init__(
            self,
            registry: CollectorRegistry,
            name: str,
            desc: str,
            redis_client: redis.Redis,
            labels: list[str] | None,
            salt_opts: dict
    ) -> None:
        self.registry = registry
        self.name = name
        self.desc = desc
        self._labels = labels
        self.redis_client = redis_client
        self.salt_opts = salt_opts
        self.master = self.salt_opts['salt_box_master_id']
        self.metric = self._create()

    @abc.abstractmethod
    def can_handle(self, tag: str) -> bool:
        """
        Determine this metric should process an event with the given tag

        :param tag: The event tag from the salt bus (e.g., 'salt/job/<jid>/...')
        """

    @property
    @abc.abstractmethod
    def labels(self) -> list[str]:
        """
        Displayed metric labels on the Grafana side
        """
        ...

    @abc.abstractmethod
    def _create(self) -> MetricWrapperBase: ...

    @abc.abstractmethod
    async def aggregate(self, tag: str, data: MessageDataType) -> None: ...


class BaseEventMetric(BaseMetric, abc.ABC):
    """
    A base metric for handling generic salt events without strict tag filtering

    This class processes all incoming events from the salt event bus
    and is intended for metrics that aggregate data across multiple
    event types, rather than filtering for specific tag patterns
    """
    def can_handle(self, tag: str) -> bool:
        return True
