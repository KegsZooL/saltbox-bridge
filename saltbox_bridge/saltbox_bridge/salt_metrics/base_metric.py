from __future__ import annotations

import abc
import re
from abc import abstractmethod

from prometheus_client import CollectorRegistry
from prometheus_client.metrics import MetricWrapperBase
from redis.asyncio.client import Redis

from saltbox_bridge.salt_handlers.base_handler import MessageDataType


class BaseMetric(abc.ABC):
    """
    A base class for handling prometheus metrics

    Attributes:
        registry: Registry of acceptable metrics
        name: Metric name
        desc: Description of the metric
        redis_client: Redis client
        salt_opts: Master config
    """
    def __init__(
            self,
            registry: CollectorRegistry,
            name: str,
            desc: str,
            redis_client: Redis,
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
    def _create(self) -> MetricWrapperBase: ...

    @property
    @abc.abstractmethod
    def labels(self) -> list[str]:
        """
        Displayed metric labels on the Grafana side
        """
        ...

    @abc.abstractmethod
    def can_handle(self, tag: str) -> bool:
        """
        Determine this metric should process an event with the given tag

        :param tag: The event tag from the salt bus (e.g., 'salt/job/<jid>/...')
        """

    @abc.abstractmethod
    async def aggregate(self, tag: str, data: MessageDataType) -> None: ...


class JobBaseMetric(BaseMetric, abc.ABC):
    """
    A base metric class for handling salt job event
    """
    @property
    @abstractmethod
    def tag_pattern(self) -> re.Pattern: ...

    @abstractmethod
    async def _aggregate(self, jid: str, data: MessageDataType) -> None: ...

    async def aggregate(self, tag: str, data: MessageDataType) -> None:
        match = self.tag_pattern.match(tag)
        if match:
            jid = match.group('jid')
            await self._aggregate(jid=jid, data=data)
